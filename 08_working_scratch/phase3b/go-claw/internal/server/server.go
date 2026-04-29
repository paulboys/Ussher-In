// Package server hosts a small read-only HTTP API for side-by-side
// verification of pilot OCR records against page images.
package server

import (
	"encoding/json"
	"fmt"
	"html"
	"net/http"
	"strconv"
	"sync"

	"github.com/paulboys/ussher-in/go-claw/internal/catchword"
	"github.com/paulboys/ussher-in/go-claw/internal/marginal"
	"github.com/paulboys/ussher-in/go-claw/internal/pilot"
)

// Store holds the loaded pilot data. It is read-only after construction.
type Store struct {
	mu    sync.RWMutex
	Pages []pilot.Page
}

// NewStore returns a Store wrapping the given pages.
func NewStore(pages []pilot.Page) *Store {
	return &Store{Pages: pages}
}

// Mux assembles the HTTP routes.
func (s *Store) Mux() *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("/", s.handleIndex)
	mux.HandleFunc("/api/pages", s.handlePages)
	mux.HandleFunc("/api/page/", s.handlePage)
	mux.HandleFunc("/api/catchword", s.handleCatchword)
	mux.HandleFunc("/api/marginalia", s.handleMarginalia)
	return mux
}

func (s *Store) handlePages(w http.ResponseWriter, _ *http.Request) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]map[string]any, len(s.Pages))
	for i, p := range s.Pages {
		out[i] = map[string]any{
			"page_num":           p.PageNum,
			"page_id":            p.PageID,
			"raw_confidence_avg": p.RawConfidenceAvg,
			"raw_confidence_min": p.RawConfidenceMin,
			"qc_status":          p.QCStatus,
		}
	}
	writeJSON(w, http.StatusOK, out)
}

func (s *Store) handlePage(w http.ResponseWriter, r *http.Request) {
	idStr := r.URL.Path[len("/api/page/"):]
	if idStr == "" {
		http.Error(w, "page id required", http.StatusBadRequest)
		return
	}
	num, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, "page id must be integer", http.StatusBadRequest)
		return
	}
	s.mu.RLock()
	defer s.mu.RUnlock()
	for _, p := range s.Pages {
		if p.PageNum == num {
			writeJSON(w, http.StatusOK, p)
			return
		}
	}
	http.Error(w, "page not found", http.StatusNotFound)
}

func (s *Store) handleCatchword(w http.ResponseWriter, _ *http.Request) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	writeJSON(w, http.StatusOK, catchword.Verify(s.Pages))
}

func (s *Store) handleMarginalia(w http.ResponseWriter, _ *http.Request) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	writeJSON(w, http.StatusOK, marginal.Extract(s.Pages))
}

func (s *Store) handleIndex(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprintf(w, `<!doctype html>
<html><head><meta charset="utf-8"><title>Claw verification</title></head>
<body>
<h1>Claw — read-only verification</h1>
<p>This server never writes to %s. The Flask annotation UI on port 5000 remains the single writer.</p>
<ul>
  <li><a href="/api/pages">/api/pages</a></li>
  <li><a href="/api/catchword">/api/catchword</a></li>
  <li><a href="/api/marginalia">/api/marginalia</a></li>
</ul>
</body></html>`, html.EscapeString("08_working_scratch/phase3b/annotations/"))
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
