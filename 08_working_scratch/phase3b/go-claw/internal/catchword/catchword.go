// Package catchword verifies that the catchword printed at the bottom of
// page N matches the first body token on page N+1.
package catchword

import (
	"strings"
	"sync"
	"unicode"

	"github.com/paulboys/ussher-in/go-claw/internal/pilot"
)

// Status enumerates the outcome of a single catchword check.
type Status string

const (
	StatusMatch    Status = "match"
	StatusMismatch Status = "mismatch"
	StatusMissing  Status = "missing"
)

// Result is the per-page verification record.
type Result struct {
	PageNum        int    `json:"page_num"`
	PageID         string `json:"page_id"`
	Status         Status `json:"status"`
	Catchword      string `json:"catchword"`
	NextFirstToken string `json:"next_first_token"`
	Detail         string `json:"detail,omitempty"`
}

// Report is the aggregate output of Verify.
type Report struct {
	Total    int      `json:"total"`
	Match    int      `json:"match"`
	Mismatch int      `json:"mismatch"`
	Missing  int      `json:"missing"`
	Results  []Result `json:"results"`
}

// FirstBodyToken returns the first whitespace-separated token of the first
// body line on the page, with leading punctuation stripped.
func FirstBodyToken(page pilot.Page) string {
	for _, line := range page.LinesByRegion("body") {
		token := firstToken(line.TextRawOCR)
		if token != "" {
			return token
		}
	}
	return ""
}

// CatchwordOf returns the catchword string for the given page (the single
// line in region 'catchword' if present).
func CatchwordOf(page pilot.Page) string {
	for _, line := range page.LinesByRegion("catchword") {
		token := firstToken(line.TextRawOCR)
		if token != "" {
			return token
		}
	}
	return ""
}

// Verify runs the catchword check across all consecutive page pairs in
// `pages` concurrently. Pages must be sorted by PageNum.
func Verify(pages []pilot.Page) Report {
	if len(pages) < 2 {
		return Report{Results: []Result{}}
	}
	results := make([]Result, len(pages)-1)
	var wg sync.WaitGroup
	for i := 0; i < len(pages)-1; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			results[idx] = verifyPair(pages[idx], pages[idx+1])
		}(i)
	}
	wg.Wait()

	report := Report{Total: len(results), Results: results}
	for _, r := range results {
		switch r.Status {
		case StatusMatch:
			report.Match++
		case StatusMismatch:
			report.Mismatch++
		case StatusMissing:
			report.Missing++
		}
	}
	return report
}

func verifyPair(current, next pilot.Page) Result {
	cw := CatchwordOf(current)
	nextTok := FirstBodyToken(next)
	res := Result{
		PageNum:        current.PageNum,
		PageID:         current.PageID,
		Catchword:      cw,
		NextFirstToken: nextTok,
	}
	if cw == "" {
		res.Status = StatusMissing
		res.Detail = "no catchword region detected on current page"
		return res
	}
	if nextTok == "" {
		res.Status = StatusMissing
		res.Detail = "no body token on next page"
		return res
	}
	if normalize(cw) == normalize(nextTok) {
		res.Status = StatusMatch
		return res
	}
	res.Status = StatusMismatch
	return res
}

func firstToken(text string) string {
	fields := strings.Fields(text)
	if len(fields) == 0 {
		return ""
	}
	return strings.TrimFunc(fields[0], func(r rune) bool {
		return unicode.IsPunct(r) || unicode.IsSymbol(r)
	})
}

func normalize(token string) string {
	// Lowercase + replace long-s with regular s for matching purposes only.
	out := strings.ToLower(token)
	out = strings.ReplaceAll(out, "ſ", "s")
	out = strings.TrimFunc(out, func(r rune) bool {
		return unicode.IsPunct(r) || unicode.IsSymbol(r)
	})
	return out
}
