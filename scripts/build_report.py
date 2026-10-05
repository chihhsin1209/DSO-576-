"""Build an evidence-based draft assignment PDF; never claims submission completion."""
import json
from pathlib import Path
from html import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
ROOT=Path(__file__).resolve().parents[1]
def main():
    reports=ROOT/'outputs/reports';audit=json.loads((reports/'audit.json').read_text());repro=json.loads((reports/'reproducibility.json').read_text());checks=json.loads((reports/'record_checks.json').read_text());rules=json.loads((ROOT/'config/cleaning_rules.json').read_text());submission=json.loads((ROOT/'config/submission.json').read_text());personal=json.loads((ROOT/'config/independent_review.json').read_text())
    assert audit['status']==repro['status']=='PASS' and all(c['pass'] for c in checks)
    notebook=json.loads((ROOT/'Module_6_Cleaning.ipynb').read_text())
    code_cells=[c for c in notebook['cells'] if c['cell_type']=='code']
    assert code_cells and all(c.get('execution_count') is not None and not any(o.get('output_type')=='error' for o in c.get('outputs',[])) for c in code_cells), 'Execute notebook successfully before report generation'
    # Direct source check, independent of the cleaning table implementation.
    source_rows={}
    with (ROOT/rules['sources']['reviews']).open() as f:
        for i,line in enumerate(f,1):
            if i in (213,6566,6567): source_rows[i]=json.loads(line)
            if i==6567: break
    independent={'method':'Direct JSONL read; full raw dictionary equality including images',
                 'full_raw_equal':source_rows[6566]==source_rows[6567],
                 'including_images':'images' in source_rows[6566],
                 'original_length':len(source_rows[213]['text']),
                 'cleaned_length':len(source_rows[213]['text'].strip()),
                 'only_trailing_nbsp_removed':source_rows[213]['text'].strip()==source_rows[213]['text'][:-1],
                 'student_personal_review':personal}
    assert independent['full_raw_equal'] and independent['including_images'] and independent['only_trailing_nbsp_removed']
    (reports/'independent_check.json').write_text(json.dumps(independent,indent=2,sort_keys=True)+'\n')
    styles=getSampleStyleSheet();story=[]
    def p(text,style='BodyText'):story.append(Paragraph(escape(text),styles[style]));story.append(Spacer(1,4))
    review_complete=all(isinstance(personal.get(k),str) and personal[k].strip() for k in ['personal_expected_result','personal_check_method','personal_conclusion'])
    p('DSO 576 Module 6 - All Beauty','Title');p('Submission metadata remains to be finalized.' if review_complete else 'Personal review and submission metadata remain to be finalized.')
    p('Question: Which parent listings have high negative-review shares, and what captured listing content is absent? One row is one retained source reviewer-product record joined to a parent listing. Review counts are not sales; repeated IDs are not deletion rules.')
    p('Source: Amazon Reviews 2023, McAuley Lab, All_Beauty. https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023')
    for k,v in rules['sources'].items():p(k+': '+v+'; SHA-256 '+audit['source_sha256_before'][k])
    p('Rule / reason / check log','Heading1')
    for k,v in rules['rules'].items():p(k+': '+v)
    p('All supplied count and rounded-metric expectations passed. Raw hashes are unchanged. See audit.json for every count, flag and denominator; missing_counts.csv and cleaned_types.csv give full field evidence.')
    story.append(PageBreak());p('Reconciliation and metrics','Heading1')
    rows=[['Measure','Observed']]+[[k,str(v)] for k,v in audit['counts'].items()]
    table=Table(rows,colWidths=[330,130],rowHeights=14,repeatRows=1);table.setStyle(TableStyle([('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8),('GRID',(0,0),(-1,-1),0.3,colors.lightgrey),('BACKGROUND',(0,0),(-1,0),colors.whitesmoke)]));story.append(table)
    metric_rows=[['Metric / denominator','Observed']]+[[k,str(v)] for k,v in audit['metrics'].items()]
    metric_table=Table(metric_rows,colWidths=[330,130],rowHeights=14,repeatRows=1)
    metric_table.setStyle(TableStyle([('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8),('GRID',(0,0),(-1,-1),0.3,colors.lightgrey)]))
    story.append(Spacer(1,8));story.append(metric_table)
    p('Observed UTC range: '+audit['timestamp_min']+' to '+audit['timestamp_max'])
    story.append(PageBreak());p('Five predeclared original / expected / actual checks','Heading1')
    for c in checks:
        p(c['id']+' - source row '+str(c['source_review_row'])+' - PASS','Heading2');p('Reason: '+c['reason']);p('Expected: '+json.dumps(c['expected']));p('Observed: '+json.dumps(c['actual']))
    p('Reproducibility','Heading1');p('PASS. '+str(len(repro['compared']))+' artifacts compared. Parquet: exact logical equality including order and dtypes; deterministic JSON/CSV: exact SHA-256. Temporary output directory; baseline outputs untouched.')
    story.append(PageBreak());p('Independent review','Heading1');p('Separate direct-source evidence: '+json.dumps({k:v for k,v in independent.items() if k!='student_personal_review'}));p('Reviewed suggestion: '+personal['suggestion'])
    p('Personal review status: '+('COMPLETE' if review_complete else 'PENDING'))
    for key in ['personal_expected_result','personal_check_method','personal_conclusion']:
        p(key.replace('_',' ').capitalize()+': '+(personal[key] if personal[key] is not None else 'PENDING'))
    p('Checklist and limitations','Heading1')
    items=['Vision/question stated','Row grain/provenance defined; composite IDs not claimed unique','Source files/hashes and reload instructions preserved','Types and conversion flags exported','Text changes and NBSP case verified','Exact raw duplicates separated from repeated IDs','Missingness preserved and counted','Suspicious values flagged','Many-to-one merge reconciled','Counts and totals reconciled','Valid denominators and unique-product price mean reported','Five predeclared records passed','Isolated rerun compared; notebook executed','Limitations: captured metadata snapshot, missing content not inferred, reviews not sales; final submission metadata pending']
    for i,x in enumerate(items,1):p(str(i)+'. '+x)
    story.append(PageBreak());p('Submission metadata','Heading1')
    for k,v in submission.items():p(k+': '+(str(v) if v is not None else 'PENDING'))
    def footer(canvas,doc):canvas.setFont('Helvetica',8);canvas.drawString(45,25,'DSO 576 | draft evidence report');canvas.drawRightString(550,25,str(doc.page))
    target=reports/'Module_6_Report.pdf';SimpleDocTemplate(str(target),rightMargin=45,leftMargin=45,topMargin=45,bottomMargin=45,allowSplitting=0).build(story,onFirstPage=footer,onLaterPages=footer);print('Generated',target)
if __name__=='__main__':main()
