package catchword

import (
	"testing"

	"github.com/paulboys/ussher-in/go-claw/internal/pilot"
)

func makePages() []pilot.Page {
	return []pilot.Page{
		{
			PageNum: 33,
			PageID:  "p0033",
			Lines: []pilot.Line{
				{Region: "body", LineIndex: 0, TextRawOCR: "Eccleſiarum antiquita-"},
				{Region: "catchword", LineIndex: 0, TextRawOCR: "tum"},
			},
		},
		{
			PageNum: 34,
			PageID:  "p0034",
			Lines: []pilot.Line{
				{Region: "body", LineIndex: 0, TextRawOCR: "tum Britannicarum"},
				{Region: "catchword", LineIndex: 0, TextRawOCR: "Liber"},
			},
		},
		{
			PageNum: 35,
			PageID:  "p0035",
			Lines: []pilot.Line{
				{Region: "body", LineIndex: 0, TextRawOCR: "Caput primum"},
			},
		},
	}
}

func TestVerifyMatchAndMismatch(t *testing.T) {
	report := Verify(makePages())
	if report.Total != 2 {
		t.Fatalf("expected 2 page-pairs, got %d", report.Total)
	}
	if report.Match != 1 {
		t.Errorf("expected 1 match, got %d (%+v)", report.Match, report.Results)
	}
	if report.Mismatch != 1 {
		t.Errorf("expected 1 mismatch, got %d (%+v)", report.Mismatch, report.Results)
	}
}

func TestVerifyMissingCatchword(t *testing.T) {
	pages := []pilot.Page{
		{PageNum: 1, PageID: "p0001", Lines: []pilot.Line{{Region: "body", TextRawOCR: "alpha"}}},
		{PageNum: 2, PageID: "p0002", Lines: []pilot.Line{{Region: "body", TextRawOCR: "beta"}}},
	}
	report := Verify(pages)
	if report.Missing != 1 {
		t.Fatalf("expected 1 missing, got %d", report.Missing)
	}
	if report.Results[0].Status != StatusMissing {
		t.Fatalf("expected missing status, got %s", report.Results[0].Status)
	}
}

func TestNormalizeLongS(t *testing.T) {
	if normalize("Eccleſiarum") != normalize("Ecclesiarum") {
		t.Fatalf("long-s normalization should treat ſ and s as equal")
	}
}

func TestVerifyEmpty(t *testing.T) {
	report := Verify(nil)
	if report.Total != 0 {
		t.Fatalf("expected 0 total, got %d", report.Total)
	}
}
