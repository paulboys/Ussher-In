package pilot

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadAndSortPages(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "pilot.json")
	body := `[
	  {"part":"part1","page_num":35,"page_id":"p0035","ocr_engine":"gemini","raw_text_path":"x","raw_confidence_avg":90,"raw_confidence_min":80,"qc_status":"pending","lines":[]},
	  {"part":"part1","page_num":33,"page_id":"p0033","ocr_engine":"gemini","raw_text_path":"x","raw_confidence_avg":91,"raw_confidence_min":80,"qc_status":"pending","lines":[
	    {"alignment_index":0,"region":"body","line_index":0,"text_raw_ocr":"abc","normalized_form":"abc","confidence":0.9}
	  ]}
	]`
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	pages, err := Load(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(pages) != 2 {
		t.Fatalf("expected 2 pages, got %d", len(pages))
	}
	if pages[0].PageNum != 33 || pages[1].PageNum != 35 {
		t.Fatalf("pages not sorted ascending: %+v", pages)
	}
	body0 := pages[0].LinesByRegion("body")
	if len(body0) != 1 || body0[0].TextRawOCR != "abc" {
		t.Fatalf("LinesByRegion failed: %+v", body0)
	}
}

func TestLoadInvalidJSON(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "bad.json")
	if err := os.WriteFile(path, []byte("{not json"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := Load(path); err == nil {
		t.Fatal("expected error from invalid JSON")
	}
}
