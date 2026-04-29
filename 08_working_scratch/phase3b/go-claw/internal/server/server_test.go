package server

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/paulboys/ussher-in/go-claw/internal/pilot"
)

func newTestStore() *Store {
	return NewStore([]pilot.Page{
		{
			PageNum:          33,
			PageID:           "p0033",
			RawConfidenceAvg: 92.5,
			Lines: []pilot.Line{
				{Region: "body", LineIndex: 0, TextRawOCR: "Eccleſiarum"},
				{Region: "catchword", LineIndex: 0, TextRawOCR: "Britan-"},
			},
		},
		{
			PageNum:          34,
			PageID:           "p0034",
			RawConfidenceAvg: 88.0,
			Lines: []pilot.Line{
				{Region: "body", LineIndex: 0, TextRawOCR: "Britan- nicarum"},
			},
		},
	})
}

func TestPagesEndpointReturnsSummary(t *testing.T) {
	srv := httptest.NewServer(newTestStore().Mux())
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/api/pages")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("got status %d", resp.StatusCode)
	}
	var out []map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		t.Fatal(err)
	}
	if len(out) != 2 {
		t.Fatalf("expected 2 pages, got %d", len(out))
	}
}

func TestSinglePageEndpointReturnsLines(t *testing.T) {
	srv := httptest.NewServer(newTestStore().Mux())
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/api/page/33")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("got status %d", resp.StatusCode)
	}
	var page pilot.Page
	if err := json.NewDecoder(resp.Body).Decode(&page); err != nil {
		t.Fatal(err)
	}
	if page.PageNum != 33 || len(page.Lines) != 2 {
		t.Fatalf("unexpected page payload: %+v", page)
	}
}

func TestUnknownPageReturns404(t *testing.T) {
	srv := httptest.NewServer(newTestStore().Mux())
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/api/page/999")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", resp.StatusCode)
	}
}

func TestCatchwordEndpointReturnsReport(t *testing.T) {
	srv := httptest.NewServer(newTestStore().Mux())
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/api/catchword")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var report struct {
		Total int `json:"total"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&report); err != nil {
		t.Fatal(err)
	}
	if report.Total != 1 {
		t.Fatalf("expected 1 page-pair, got %d", report.Total)
	}
}
