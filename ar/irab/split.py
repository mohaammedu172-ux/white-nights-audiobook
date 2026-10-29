import re, json, sys
lines = open('/root/irab/durra/v1_djvu.txt', encoding='utf8').read().split('\n')[925:6600]
txt = '\n'.join(lines)
# i'rab blocks: from 'الإعراب :' to the next 'المعنى' heading or verse-number header
starts = [m.start() for m in re.finditer(r'(?m)^\s*ال\S{0,2}عراب\s*[:8;؛]', txt)]
blocks = []
for i, s in enumerate(starts):
    end = starts[i + 1] if i + 1 < len(starts) else len(txt)
    seg = txt[s:end]
    # cut at the next verse header line: number/OCR digit then ' - ' then verse text, or a page header
    m = re.search(r'(?m)^\s*(\S{1,3})\s*-\s*\S.*$', seg[20:])
    cut = 20 + m.start() if m else len(seg)
    seg = seg[:cut]
    seg = re.sub(r'(?m)^\s*(معلقة امرىء القيس|[٠-٩0-9۰-۹]+)\s*$', '', seg)
    blocks.append(re.sub(r'\n\s*\n+', '\n', seg).strip())
json.dump(blocks, open('/root/irab/work/blocks.json', 'w'), ensure_ascii=False, indent=1)
print(len(blocks)); print(blocks[1][:600])
