// Package pilot parses the JSON records emitted by the Python pilot OCR
// pipeline (08_working_scratch/pipeline_scripts/pilot_ocr.run_gemini_pilot).
package pilot

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
)

// Line mirrors the per-line entries inside a pilot record's "lines" array.
type Line struct {
	AlignmentIndex        int     `json:"alignment_index"`
	Region                string  `json:"region"`
	LineIndex             int     `json:"line_index"`
	TextRawOCR            string  `json:"text_raw_ocr"`
	NormalizedForm        string  `json:"normalized_form"`
	Confidence            float64 `json:"confidence"`
	Illegible             bool    `json:"illegible"`
	MarkerID              string  `json:"marker_id"`
	MarginaliaAnchorIndex *int    `json:"marginalia_anchor_index,omitempty"`
}

// Page mirrors a single record from the pilot_ocr.json output array.
type Page struct {
	Part             string   `json:"part"`
	PageNum          int      `json:"page_num"`
	PageID           string   `json:"page_id"`
	OCREngine        string   `json:"ocr_engine"`
	OCRProviderModel string   `json:"ocr_provider_model,omitempty"`
	OCRLang          []string `json:"ocr_lang"`
	RawTextPath      string   `json:"raw_text_path"`
	RawConfidenceAvg float64  `json:"raw_confidence_avg"`
	RawConfidenceMin float64  `json:"raw_confidence_min"`
	PageSummary      string   `json:"page_summary,omitempty"`
	Lines            []Line   `json:"lines"`
	QCStatus         string   `json:"qc_status"`
}

// LinesByRegion returns the subset of lines whose region matches `region`,
// preserving the order they appeared in the source JSON.
func (p Page) LinesByRegion(region string) []Line {
	out := make([]Line, 0, len(p.Lines))
	for _, line := range p.Lines {
		if line.Region == region {
			out = append(out, line)
		}
	}
	return out
}

// Load reads a pilot OCR JSON file and returns the pages sorted by PageNum.
func Load(path string) ([]Page, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read pilot json: %w", err)
	}
	var pages []Page
	if err := json.Unmarshal(data, &pages); err != nil {
		return nil, fmt.Errorf("parse pilot json: %w", err)
	}
	sort.Slice(pages, func(i, j int) bool { return pages[i].PageNum < pages[j].PageNum })
	return pages, nil
}
