// Package marginal extracts scripture/citation references printed in the
// outer margin of the page so they can be indexed into research JSON.
package marginal

import (
	"regexp"
	"strings"

	"github.com/paulboys/ussher-in/go-claw/internal/pilot"
)

// Reference is a single extracted marginal reference.
type Reference struct {
	PageNum     int    `json:"page_num"`
	PageID      string `json:"page_id"`
	AnchorIndex int    `json:"anchor_index"` // body line index this marginalia anchors to (-1 if unknown)
	Text        string `json:"text"`
	Citation    string `json:"citation,omitempty"` // canonical form when recognized (e.g. "Gen. 1:1")
	Kind        string `json:"kind"`               // "scripture", "classical", "unknown"
}

// scripturePattern matches a leading book abbreviation + chapter[.verse] form.
// e.g. "Gen. 1.1", "Matth. 5. 3-12", "1 Reg. 8.27".
var scripturePattern = regexp.MustCompile(
	`^(?P<book>(?:1|2|3)?\s?[A-Z][a-z]{1,7}\.?)\s+(?P<chapter>\d+)(?:[.,:]\s*(?P<verse>\d+(?:[-–]\d+)?))?`,
)

// Extract walks all pages and returns marginalia references as a flat list
// suitable for emitting as a JSON index alongside the research database.
func Extract(pages []pilot.Page) []Reference {
	out := make([]Reference, 0, 64)
	for _, page := range pages {
		for _, line := range page.LinesByRegion("marginalia") {
			ref := classify(line.TextRawOCR)
			ref.PageNum = page.PageNum
			ref.PageID = page.PageID
			if line.MarginaliaAnchorIndex != nil {
				ref.AnchorIndex = *line.MarginaliaAnchorIndex
			} else {
				ref.AnchorIndex = -1
			}
			out = append(out, ref)
		}
	}
	return out
}

func classify(text string) Reference {
	text = strings.TrimSpace(text)
	ref := Reference{Text: text, Kind: "unknown"}
	if text == "" {
		return ref
	}
	if match := scripturePattern.FindStringSubmatch(text); match != nil {
		ref.Kind = "scripture"
		ref.Citation = canonicalize(match)
		return ref
	}
	return ref
}

func canonicalize(match []string) string {
	book := strings.TrimSpace(match[1])
	chapter := strings.TrimSpace(match[2])
	verse := ""
	if len(match) > 3 {
		verse = strings.TrimSpace(match[3])
	}
	out := book + " " + chapter
	if verse != "" {
		out += ":" + verse
	}
	return out
}
