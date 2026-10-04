"""Build the assignment PDF and README from verified cleaning evidence."""
import csv,html,json,pathlib,sys
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(name):return json.loads((ROOT/'outputs'/name).read_text())
def main():
    pdfmetrics.registerFont(TTFont('TaskSans',str(ROOT/'assets/fonts/DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('TaskSans-Bold',str(ROOT/'assets/fonts/DejaVuSans-Bold.ttf')))
    a=load('audit.json');v=load('verification.json');rep=load('reproducibility.json');nb=load('notebook_execution.json');checks=load('record_checks.json');m=json.loads((ROOT/'submission_metadata.json').read_text())
    assert v['passed'] and rep['passed'] and nb['all_code_cells_completed']
    rev=a['tables']['reviews'];meta=a['tables']['metadata'];metrics=a['metrics'];merge=a['merge'];dups=a['duplicates'];sus=a['suspicious']
    commit=m['submitted_commit'];pending=commit=='PENDING_USER_PUSH'
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCustom',fontName='TaskSans-Bold',fontSize=20,leading=25,textColor=colors.HexColor('#16324f'),spaceAfter=12))
    styles.add(ParagraphStyle(name='BodyCustom',fontName='TaskSans',fontSize=9,leading=13,spaceAfter=7))
    styles.add(ParagraphStyle(name='SmallCustom',fontName='TaskSans',fontSize=8,leading=10.5,spaceAfter=4))
    styles.add(ParagraphStyle(name='CellCustom',fontName='TaskSans',fontSize=8,leading=10))
    styles['Heading2'].fontName='TaskSans-Bold';styles['Heading2'].textColor=colors.HexColor('#16324f');styles['Heading2'].fontSize=12;styles['Heading2'].leading=15;styles['Heading2'].spaceBefore=10
    def para(text,style='BodyCustom'):return Paragraph(html.escape(str(text)).replace('\n','<br/>'),styles[style])
    def table(rows,widths,header=True):
        t=Table([[para(x,'CellCustom') for x in row] for row in rows],colWidths=widths,repeatRows=1 if header else 0,hAlign='LEFT')
        commands=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#52718f')),('GRID',(0,0),(-1,-1),.25,colors.HexColor('#d3dce5'))]
        if header:commands += [('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf2f7'))]
        t.setStyle(TableStyle(commands));return t
    story=[]
    def title(t):story.extend([para(t,'TitleCustom'),Spacer(1,4)])
    def item(n,t,text):story.extend([Paragraph(f'{n}. {html.escape(t)} <font color="#356847">[Done]</font>',styles['Heading2']),para(text)])
    title('Module 6 | Data Cleaning')
    story.append(para('Wayne J. Chen | DSO 576 | Individual assignment'))
    story.append(para('Project: Amazon Beauty Product-Listing Quality'))
    story.append(table([['Result','Full-data evidence'],['Review rows','701,528 original - 7,275 exact duplicates = 694,253 retained'],['Product metadata','112,590 original and retained; 0 exact duplicates; 0 conflicting parent keys'],['Merge','694,253 reviews before and after left join; all matched; 25 metadata products have no retained reviews'],['Verification','Five genuine records passed; all 50 sample rows checked; fresh-process outputs match']], [132,372]))
    story.append(Spacer(1,10));story.append(para('Branch: '+m['branch']));story.append(para('Branch URL: '+m['branch_url'],'SmallCustom'))
    story.append(para('Submitted commit ID: '+('PENDING - insert the real code/evidence commit after your GitHub push.' if pending else commit),'SmallCustom'))
    story.append(para('Source branch ZIP snapshot: '+m['source_snapshot_commit']+' (this is the original branch snapshot, not the new cleaning submission).','SmallCustom'))
    item(1,'State the project vision and question','A Beauty category manager must decide which listings to review first for possible missing or unclear information raised repeatedly in reviews. The intended main metric is distinct retained reviews mentioning the same theme per parent product (at least two), compared with listing coverage. This cleaning assignment prepares those fields and verifies review counts, average rating, negative-review rate, and purchase rate; it does not claim to have validated listing gaps. The newer project vision uses All Beauty and takes precedence over the older Appliances proposal in the ZIP.')
    item(2,'Define one row','One review row is one source review event; one metadata row is one parent listing. The review source has no guaranteed unique natural key. The retained identifier All_Beauty:{source_line:07d} uniquely locates the original review line. Distinct rows sharing (user_id, asin, timestamp) remain separate and flagged. Metadata parent_asin is unique in the checked full file; reviews join many-to-one to it. Evidence: scripts/clean_data.py; outputs/audit.json; SQLite schema and review_products view.')
    item(3,'Preserve the source','Source: McAuley-Lab Amazon Reviews 2023, HF revision '+a['source']['revision']+'. Download date: 2026-10-04 in Los Angeles. Both full category JSONL files are read only; SHA-256 and byte sizes are checked before and after cleaning. The metadata JSONL is used instead of the preliminary parquet; equal row counts do not imply byte-equivalence. Load with scripts/download_data.py; paths and checksums appear in source_manifest.json. Raw files are excluded from Git and the ZIP and can be downloaded at the pinned revision.')
    story.append(PageBreak());title('Checklist | Types and missing data')
    item(4,'Inspect columns and types','All 701,528 original review ratings are floats; the 694,253 retained valid integer ratings become integers in 1..5. IDs remain strings. Timestamps remain integer milliseconds and gain UTC ISO datetime strings. Purchase flags remain booleans in JSON (SQLite stores them as 0/1). Helpful votes and listing rating counts stay integers; listing prices and average ratings stay floats. Empty prose becomes null. Nested features, description, details, images, videos, and categories retain their list/dictionary structures. Failed conversions: 0 across every checked field; invalid numeric domains: 0. Evidence: outputs/column_audit.csv covers every source column; source/cleaned types and changed-value counts are explicit.')
    item(5,'Standardize text',f"Use NFC, decode HTML entities, replace br tags with newlines, and trim outer whitespace. Preserve case, punctuation, typos, internal spacing, non-br markup, variant distinctions, and ID leading zeros. Changed retained review bodies: {rev['changed_fields']['text']:,}; headlines: {rev['changed_fields']['title']:,}. Metadata changes: 22 titles, 58 features lists, 10 description lists, 297 details dictionaries. Real source line 37 changes 'when<br />one' to 'when\\none'; line 19,599 changes '&amp;' to '&'; line 9,585 keeps '0816091846'. Evidence: five record checks and column audit.")
    item(6,'Investigate duplicates',f"Count original JSON objects before normalization, including nested fields. Exactly {rev['exact_duplicate_rows_removed']:,} duplicate reviews are removed, keeping the first source line; metadata exact duplicates: 0. Raw candidate-key groups repeated: {dups['raw_repeated_review_candidate_groups']:,}, involving {dups['raw_rows_in_repeated_review_candidate_groups']:,} rows. After exact deduplication, one candidate-key group still has two distinct records; both remain. Repeated user/product IDs are expected and are not duplicate evidence. Retained repeated-ID counts are recorded in audit.json; mappings are in removed_duplicates.csv. Example: source line 6,567 is an exact repeat of 6,566. Metadata parent-key conflicts: 0.")
    item(7,'Handle missing data','Review text missing: 107 original; 106 after exact deduplication but before text cleaning; 705 after text cleaning. The extra 599 are whitespace/formatting-only bodies recognized as empty. All 705 review rows remain; their valid ratings still count, and they are excluded only from body-text analysis. Metadata price missing: 94,886; store: 11,331; title: 12; features: 95,213 empty lists; description: 93,428 empty lists; details: 4,512 empty dictionaries. These counts stay unchanged. Categories and bought_together contain no supplied content in all 112,590 products. No statistical imputation is performed. Empty attachment lists mean no attachments, not a failed review. Appendix table reports every affected column at all three stages.')
    story.append(PageBreak());title('Checklist | Result validation')
    item(8,'Check suspicious values',f"All retained ratings are integers in 1..5; helpful votes and rating counts are nonnegative integers; available prices are finite and nonnegative. All {metrics['in_scope_date_n']:,} dates are within the documented May 1996-September 2023 window; observed range is {metrics['date_min'][:10]} to {metrics['date_max'][:10]} UTC. Helpful votes: 99th-percentile order statistic {sus['helpful_vote_p99']}, maximum {sus['max_helpful_vote']}; both are retained. Price range: {sus['min_price']:.2f} to {sus['max_price']:.2f}; these are snapshot list prices, not sales. Numeric-looking product 0816091846 looks unrelated to beauty and is kept for taxonomy review. All products lack categories, so category validation remains a limitation, documented rather than silently corrected.")
    item(9,'Verify merges',f"Left join reviews to metadata on parent_asin, expected many-to-one. Metadata has {merge['eligible_metadata_rows']:,} eligible unique keys. Reviews before merge: {rev['retained_rows']:,}; after: {merge['joined_rows']:,}; unexpected extra rows: 0. Unmatched review rows: {merge['unmatched_review_rows']}; unmatched nonmissing parent keys: {merge['unmatched_parent_keys']}; missing review join keys: {merge['missing_parent_key_rows']}. Matched distinct parents: {merge['matched_parent_keys']:,}; unused metadata parents: {merge['metadata_without_reviews']}. Missing keys would not match and unmatched reviews would be retained. Assertions enforce row conservation. Evidence: audit.json merge section, unmatched_products.csv, metadata_conflicting_keys.csv.")
    item(10,'Reconcile changes','Reviews: 701,528 - 7,275 exact duplicate rows = 694,253. No other review rows are dropped. Metadata: 112,590 - 0 = 112,590. Rating sum: 2,778,223 - 28,361 duplicate rating points = 2,749,862. Helpful-vote sum: 647,923 - 6,313 duplicate votes = 641,610. Rating average changes from 3.960245 to 3.960893 after deduplication. Metadata rating_number sum stays 5,690,450. Available price sum stays 482,535.44 to cent precision (17,704 known prices); this is only a reconciliation diagnostic, not revenue. Merge adds no reviews or rating/helpful totals. Independent raw rescan agrees with cleaned counts and sums; floating-point price accumulation is interpreted at cent precision.')
    item(11,'Check calculations',f"Mean review rating = {metrics['rating_sum']:,}/{metrics['rating_n']:,} = {metrics['average_rating']:.6f}. Negative-review rate uses 1-2 star ratings: {metrics['negative_review_n']:,}/{metrics['rating_n']:,} = {metrics['negative_review_rate']:.4%}. Verified-purchase rate = {metrics['verified_purchase_n']:,}/{metrics['purchase_n']:,} = {metrics['verified_purchase_rate']:.4%}. Helpful-vote total uses {metrics['helpful_n']:,} known vote counts. Text-body analysis denominator: {metrics['review_body_n']:,}; time metrics: {metrics['in_scope_date_n']:,}. Product metrics exclude missing parent keys and report the excluded count (0). Metadata average_rating and rating_number are listing snapshots and are not substituted into review averages. Price analyses use known prices only; no weighted sales average is inferred. Evidence: product_metrics.csv, annual_metrics.csv, audit.json metrics, verify_outputs.py.")
    story.append(PageBreak());title('Checklist | Evidence and reproducibility')
    item(12,'Verify individual records','Five genuine source records were assigned explicit expected values before the completed verification run. Cases cover HTML breaks, entity decoding with doubled spaces, missing text with a retained rating, a leading-zero identifier, and a matched product with missing price. The expectations are literal values or independent source lookups, not values generated by the cleaning function. All five match actual output. Full values and reasons: docs/record_expectations.json and outputs/record_checks.json. The record-check pages below show original, expected, and actual values. These are real records; the separate five boundary probes are explicitly synthetic.')
    item(13,'Test reproducibility',f"The notebook's {nb['code_cell_count']} code cells were run in order in a fresh Python process with an IPython namespace using scripts/execute_notebook.py. A socket-backed Jupyter kernel was unavailable in this environment, so the execution method is reported explicitly; all actual cell outputs are stored in the notebook. A second fresh Python process rebuilt the full data from the preserved originals. All {rep['compared_artifact_count']} deterministic CSV/JSON/JSONL output hashes match, the logical database fingerprint matches, and independent verification matches. Commands: python scripts/execute_notebook.py; python scripts/reproduce.py. The README lists pinned dependencies and expected files. Evidence: notebook_execution.json, reproducibility.json, output_checksums.json. Commit metadata must be finalized after the user pushes the package.")
    item(14,'Document remaining limitations','Data validation issues remaining: taxonomy cannot be confirmed because categories are empty; the retained repeated candidate key cannot be resolved without upstream review IDs or edit history; missing listing content and prices remain unknown. Historical reviews/listings are not current Amazon pages. Keyword mentions alone cannot establish missing or unclear information, causation, or business impact. Review counts and helpful votes are feedback activity, not sales. The deterministic 50-row audit sample and the earlier 1 MiB sample are not representative. Future listing decisions require authorized current listing snapshots, manual theme/coverage checks, and internal sales, conversion, return, or margin data. Raw reviews and listing copies may differ in observation time. A meaningful title can remain even when body text is missing; body-text theme analysis must state its denominator.')
    story.append(Paragraph('How a Codex suggestion was checked',styles['Heading2']))
    story.append(para("Codex suggested decoding entities and replacing HTML line breaks to make review evidence readable. That could alter meaningful characters or remove word boundaries. Literal expected strings were checked against actual outputs for source lines 37 and 19,599; the first preserves the typo 'Rrain' and inserts newlines, and the second preserves doubled spaces while decoding '&amp;'. The checks do not call the prose-cleaning function to calculate their expected values. A separately labeled synthetic probe checks that 'I love it <3' survives unchanged. Result: five real checks pass and five boundary probes pass. Wayne should review these decisions and evidence before submitting."))
    story.append(PageBreak());title('Cleaning decision log')
    log=[['Rule','Reason / exception','Check and result'],
    ['Pin source revision; read originals only','Catch wrong or interrupted downloads; source JSONL differs from preliminary parquet format.','Both published SHA-256 hashes and sizes match; input hashes unchanged.'],
    ['IDs remain strings; trim only','ASINs can be numeric-looking; case and leading zeros matter.','0 ID value changes; line 9,585 keeps 0816091846.'],
    ['NFC + entity decode + br replacement + outer trim','Readability for text evidence; keep case, typos, internal spacing and non-br markup.','53,270 bodies / 154 headlines changed; literal cases 37 and 19,599 pass.'],
    ['Blank human prose -> null; keep nested structures','Missing body does not invalidate rating; empty features/description do not prove a theme gap.','106 retained blank bodies before -> 705 null bodies after; rows retained.'],
    ['Validate numeric types and UTC milliseconds','Reject booleans as numbers; null invalid values, never invent zero.','0 failed conversions / invalid domains; all retained dates in documented scope.'],
    ['Remove only exact original-object duplicates','Do not collapse different variant/reviewer events or deduplicate by normalized text.','7,275 removed; mapping emitted; rating/helpful totals fully reconcile.'],
    ['Keep distinct repeated candidate keys; flag','Natural review identity is not guaranteed; upstream IDs unavailable.','One group / two distinct rows kept; exact duplicates counted separately.'],
    ['Metadata keys must be unique; left join','Conflicting listing records must not multiply review evidence.','0 metadata conflicts; 694,253 rows conserved; 0 unmatched reviews; 25 unused products.'],
    ['Keep missing price/store/listing content','Imputed zero or guessed prose could distort prioritization.','94,886 missing prices retained; known-price denominator 17,704.'],
    ['Keep valid extreme values and taxonomy anomalies','Unusual is not automatically wrong; incomplete categories prevent reliable exclusion.','Maximum votes 646 and price 2,548.98 retained; all 112,590 category lists empty.'],
    ['Use metric-specific denominators','Null text affects theme analysis, not a valid rating; missing group keys excluded explicitly.','Rating/purchase n=694,253; body n=693,548; null product-key exclusions=0.'],
    ['Share 50 genuine audit rows deterministically','Cover hard cases, then diversify by hashed source identifier; not a statistical sample.','50 unique rows match full stored records and metadata; JSONL preserves types.']]
    story.append(table(log,[131,185,188]));story.append(Spacer(1,8));story.append(para('Rules were written before the cleaning pipeline. The full initial scan inspected all records; no raw records were edited. Expected checks are stored separately from transformation code. Evidence paths are relative to the package root.','SmallCustom'))
    story.append(PageBreak());title('Five genuine record checks | 1-3')
    def show(c):
        story.append(Paragraph(f"Source line {c['source_line']:,}: {html.escape(c['case'])}",styles['Heading2']))
        rows=[['Stage','Value']]
        for k in ['original','expected','actual']:
            rows.append([k.capitalize(),json.dumps(c[k],ensure_ascii=False)])
        story.append(table(rows,[62,442]));story.append(para('Reason: '+c['reason']));story.append(para('Matches expected: YES','SmallCustom'))
    for c in checks[:3]:show(c)
    story.append(PageBreak());title('Five genuine record checks | 4-5')
    for c in checks[3:]:show(c)
    story.append(Paragraph('Difficult-case sample',styles['Heading2']))
    story.append(para('The first sample records are the five real checks above. Additional cases cover repeated candidate keys, missing listing descriptions or features, low ratings, and high helpful votes where available. Remaining slots are chosen by ascending SHA-256(record_id), making selection repeatable without favoring the first 50 source rows. No unmatched example exists in this full category; none is invented. All 50 JSONL/CSV records retain source line references and an explicit sample_reason. JSONL is authoritative for types; CSV should be loaded with string dtypes for identifiers.'))
    story.append(PageBreak());title('Missingness appendix | All affected columns')
    rows=[['Table / column','Raw','Retained before text cleaning','Cleaned','Treatment']]
    for kind,t in [('reviews',rev),('metadata',meta)]:
        for k in sorted(t['raw_profile']['types']):
            raw=t['raw_profile']['missing'].get(k,0);before=t['retained_before_cleaning_profile']['missing'].get(k,0);after=t['cleaned_profile']['missing'].get(k,0)
            if raw or after:
                treatment='Keep empty attachment list' if k in ['images','videos'] else 'Keep empty list/dict' if k in ['features','description','details','categories'] else 'Keep null; no imputation'
                rows.append([kind+'/'+k,f'{raw:,}',f'{before:,}',f'{after:,}',treatment])
    story.append(table(rows,[135,64,100,64,141]));story.append(Spacer(1,10))
    story.append(para('Missingness means null, empty string, empty list, or empty dictionary, according to the column structure. The three stages distinguish duplicate removal from normalization. For review text, one missing original body is removed as an exact duplicate; 599 additional retained bodies become null after formatting/whitespace is removed. Empty lists are retained as lists, not replaced by null. No numeric or identifier field has missing values except listing price.','SmallCustom'))
    story.append(Paragraph('Source integrity and rerun evidence',styles['Heading2']))
    for spec in a['source']['files']:
        story.append(para(f"{spec['filename']}: {spec['rows']:,} rows; {spec['size']:,} bytes; SHA-256 {spec['sha256']}",'SmallCustom'))
    story.append(para('Logical cleaned database SHA-256: '+a['logical_database_sha256'],'SmallCustom'))
    story.append(para('Source reference: https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023\nProject source: uploaded DSO_576_Project_Vision.pdf; earlier branch snapshot 14d977ee9dc441249520bb74b17cabaa72ab874e.\nFull evidence: outputs/audit.json, column_audit.csv, verification.json, reproducibility.json, notebook_execution.json, and five record_checks.json entries.','SmallCustom'))
    path=ROOT/'Wayne_Chen_Module_6_Report.pdf'
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#d3dce5'));canvas.line(54,40,558,40);canvas.setFont('TaskSans',8);canvas.setFillColor(colors.HexColor('#52718f'));canvas.drawString(54,28,'Wayne J. Chen | DSO 576 | Full All Beauty data cleaning');canvas.drawRightString(558,28,str(doc.page))
    SimpleDocTemplate(str(path),pagesize=(612,792),leftMargin=54,rightMargin=54,topMargin=45,bottomMargin=52,title='Wayne Chen - Module 6 Data Cleaning',author='Wayne J. Chen').build(story,onFirstPage=footer,onLaterPages=footer)
    # README regenerated from evidence so its counts cannot drift from the PDF.
    readme=f'''# Module 6 - Wayne J. Chen: All Beauty data cleaning

- Branch: `{m['branch']}`
- Branch URL: {m['branch_url']}
- Submitted commit ID: `{commit}`
- Source ZIP snapshot commit: `{m['source_snapshot_commit']}` (old branch, not new submission).

{'**Before submitting:** replace the pending commit by running the finalization command below after committing/pushing your work.' if pending else 'The submitted SHA identifies the code and cleaning evidence. PDF/README commit metadata may be added in a later documentation-only commit.'}

## Project and source

The newer uploaded project vision uses **All Beauty**. The older branch's Appliances proposal is preserved in `docs/project-start.md` for provenance, and is superseded for this assignment. A Beauty category manager wants to prioritize listings for possible missing or unclear information mentioned repeatedly by customers. Planned main comparison: distinct review mentions of a theme per parent listing (at least two) against listing coverage. This assignment cleans and validates data, without claiming to prove information gaps.

Dataset: https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023
Pinned HF revision: `{a['source']['revision']}`. Download date: 2026-10-04 (Los Angeles).

Inputs are the **full category**: `All_Beauty.jsonl` ({rev['raw_rows']:,} reviews, 326,611,506 bytes) and `meta_All_Beauty.jsonl` ({meta['raw_rows']:,} listings, 212,990,142 bytes). The raw metadata JSONL is used instead of the preliminary parquet. Its full row count is checked, but byte-equivalence with that parquet is not claimed. `source_manifest.json` pins source paths, byte sizes, and published SHA-256 checksums. Originals are read only; downloads are atomic and verified. No remote loading script is executed.

## Run from the package root

Python 3.12 was used. Cleaning/download/reproduction scripts use the standard library. The notebook and PDF require the listed dependencies. Allow about 3 GB of free disk for raw data, the database and its reproduction; memory is bounded by streaming plus an independent fingerprint set.

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell instead: .venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python scripts/download_data.py
python scripts/execute_notebook.py
python scripts/reproduce.py
python scripts/build_report.py
```

The downloader needs internet access; subsequent cleaning can run offline from verified originals. To run scripts without the notebook:

```bash
python scripts/clean_data.py
python scripts/verify_outputs.py
python scripts/reproduce.py
python scripts/build_report.py
```

Alternatively open `cleaning_waynechen.ipynb` in VS Code/Jupyter, select the environment, **Restart Kernel**, then **Run All**. The supplied notebook was actually executed in a new Python process/IPython namespace through `execute_notebook.py`; it did not use a socket-backed Jupyter server in this environment. Actual cell outputs and `outputs/notebook_execution.json` record the method honestly. `reproduce.py` independently reruns the full cleaner in another process and compares deterministic output hashes. Specify `--raw-dir PATH --out PATH` on the cleaner/verifier for custom locations; `reproduce.py` accepts `--raw-dir PATH --baseline PATH`.

## Expected results and files

- `{rev['raw_rows']:,} - {rev['exact_duplicate_rows_removed']:,} = {rev['retained_rows']:,}` retained reviews; metadata stays `{meta['retained_rows']:,}`.
- Many-to-one left join on `parent_asin` conserves `{merge['joined_rows']:,}` rows; unmatched reviews `0`; metadata with no retained reviews `25`.
- Rating sum `{metrics['rating_sum']:,}`; helpful votes `{metrics['helpful_vote_sum']:,}`; mean rating `{metrics['average_rating']:.6f}`; negative-review rate `{metrics['negative_review_rate']:.4%}`; verified-purchase rate `{metrics['verified_purchase_rate']:.4%}`.
- Five genuine checks and all 50 sample membership/field checks pass. `{rep['compared_artifact_count']}` deterministic output files match on full rerun.

`outputs/cleaned.sqlite` (generated, excluded from ZIP/Git) contains `reviews`, `metadata`, `removed_duplicates`, `repeated_review_keys`, `metadata_conflicting_keys` and `review_products`/`eligible_metadata` views. `payload` stores typed JSON including nested source columns. SQLite purchase flags are 0/1; JSON flags remain booleans. Product columns are accessed through the left-join view. Full cleaned review data need not be committed; the instructor can recreate it from pinned originals.

Committed evidence:
- `outputs/audit.json`, `column_audit.csv`: full-dataset counts, missingness, types, changes, flags, totals and join coverage.
- `outputs/removed_duplicates.csv`, `repeated_review_keys.csv`, `metadata_conflicting_keys.csv`, `unmatched_products.csv`: exact-duplicate mappings and key audits (empty tables retain headers).
- `outputs/product_metrics.csv`, `annual_metrics.csv`: complete **aggregated** metric tables, not extra review samples.
- `outputs/record_checks.json`, `verification.json`: original/expected/actual cases and independent raw-to-output checks.
- `outputs/output_checksums.json`, `reproducibility.json`, `notebook_execution.json`: deterministic result and rerun evidence.
- `outputs/samples/cleaned_sample.jsonl` and `.csv`: **50 real joined review records**. Difficult cases first, remaining slots by SHA-256(record_id). This audit sample is not representative. JSONL preserves types; CSV must load `asin`, `parent_asin`, and `user_id` as strings (see notebook).
- `docs/cleaning_rules.md`, `record_expectations.json`: rules and expectations separate from transformation code.
- `Wayne_Chen_Module_6_Report.pdf`: individual Gradescope report with all 14 checklist items, decision log and five record checks.

## Decisions and limitations

Exact duplicates are removed based on full original parsed records, before normalization. Distinct repeated `(user_id, asin, timestamp)` records stay flagged; no natural unique review key is assumed. Identifiers retain leading zeros/case. Normalize human prose conservatively; retain punctuation, typos, internal spacing, non-br markup, and nested lists/dictionaries. No unsupported imputation is made. Review-body denominator is `{metrics['review_body_n']:,}`; known rating and purchase denominators are `{metrics['review_count']:,}`. Products with missing grouping keys would be excluded and counted (0 here). Missing listing prices remain unknown, not zero; count of known prices is `17,704`.

All metadata category lists are empty; taxonomy anomalies and the retained repeated candidate key require later manual/source review. Historical listings are not current Amazon pages. Missing copy or keyword mentions cannot prove a listing gap, causality, sales, conversion or ROI. `rating_number` is feedback reach, not sales. Current authorized listing snapshots and business metrics are required for actionable conclusions. Review all Codex decisions and record checks before submitting.

## Push and finalize your submission

Keep this folder inside your repository, e.g. `cleaning_waynechen/`. Preserve the team's existing root files. Switch to your own branch; never push to main or the course repository.

From the repository root:

```bash
git switch cleaning-waynechen
git add cleaning_waynechen
git commit -m "Add Wayne Module 6 cleaning and full-data verification"
git push origin cleaning-waynechen
git rev-parse HEAD
```

Copy that full 40-character **code/evidence commit**. From this folder run:

```bash
python scripts/finalize_submission.py --commit YOUR_40_CHARACTER_CODE_COMMIT
```

This updates the PDF and README to cite the real pushed code/evidence commit; no commit is invented. Then commit/push the updated `submission_metadata.json`, README and PDF as a documentation update. The cited code/evidence commit remains stable and identifies the exact cleaning code and outputs underlying the report; the latest documentation records that SHA.

Submit the regenerated **single PDF** to Gradescope yourself. Give your instructor repository access as the assignment requires. The ZIP is a transfer package, not the Gradescope submission. Git push/instructor access/Gradescope submission are user tasks and were not performed here.
'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8');print(path)
if __name__=='__main__':main()
