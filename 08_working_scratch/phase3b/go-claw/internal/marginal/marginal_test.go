package marginal

import (
	"testing"

	"github.com/paulboys/ussher-in/go-claw/internal/pilot"
)

func TestExtractScriptureReference(t *testing.T) {
	anchor := 4
	pages := []pilot.Page{
		{
			PageNum: 33,
			PageID:  "p0033",
			Lines: []pilot.Line{
				{Region: "body", LineIndex: 0, TextRawOCR: "..."},
				{Region: "marginalia", LineIndex: 0, TextRawOCR: "Gen. 1.1", MarginaliaAnchorIndex: &anchor},
				{Region: "marginalia", LineIndex: 1, TextRawOCR: "Cic. de Off."},
			},
		},
	}

	refs := Extract(pages)
	if len(refs) != 2 {
		t.Fatalf("expected 2 references, got %d", len(refs))
	}
	if refs[0].Kind != "scripture" {
		t.Errorf("expected scripture, got %q", refs[0].Kind)
	}
	if refs[0].Citation != "Gen. 1:1" {
		t.Errorf("expected canonical 'Gen. 1:1', got %q", refs[0].Citation)
	}
	if refs[0].AnchorIndex != 4 {
		t.Errorf("expected anchor=4, got %d", refs[0].AnchorIndex)
	}
	if refs[1].Kind != "unknown" {
		t.Errorf("expected unknown classification, got %q", refs[1].Kind)
	}
}

func TestExtractHandlesPagesWithoutMarginalia(t *testing.T) {
	pages := []pilot.Page{
		{PageNum: 1, PageID: "p0001", Lines: []pilot.Line{{Region: "body", TextRawOCR: "x"}}},
	}
	refs := Extract(pages)
	if len(refs) != 0 {
		t.Fatalf("expected 0 references, got %d", len(refs))
	}
}
