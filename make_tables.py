"""Generate manuscript-ready Markdown tables from actual saved outputs."""
from pathlib import Path
import argparse
import json
import pandas as pd


def markdown(headers, rows):
    def safe(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] + ['| ' + ' | '.join(map(safe, row)) + ' |' for row in rows])


def pformat(value):
    return '<.001' if value < .001 else f'{value:.3f}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('results'))
    args = parser.parse_args()
    out = args.out
    audit = json.loads((out / 'audit.json').read_text())
    models = pd.read_csv(out / 'model_results.csv')
    desc = pd.read_csv(out / 'descriptives.csv', header=[0, 1], index_col=0)
    sections = ['# 실제 출력에서 생성한 결과표', '이 표는 실행 결과를 포맷하며 원고의 결론을 자동 갱신하지 않습니다. 관련성은 인과 효과가 아닙니다.']
    sections += ['## 연결·제외 기록을 통해 분석 표본을 확인했다.', markdown(['지표', '값'], [
        ['연결 세션', audit['joined_sessions']], ['주분석 세션', audit['primary_sessions']],
        ['참여자 ID', audit['primary_workers']], ['창작 세션', audit['primary_genres']['creative']],
        ['논증 세션', audit['primary_genres']['argumentative']], ['원본 SHA-256', audit['sha256']]])]
    descriptive = []
    for variable, label in [('ownership','소유감'),('understanding','지각된 이해'),('ideation','아이디어 도움'),('written_by_human','인간 작성 비율(%)'),('num_query','요청 횟수'),('time','소요 시간(분)')]:
        descriptive.append([label] + [f'{desc.loc[g, (variable,"mean")]:.3f} ({desc.loc[g, (variable,"std")]:.3f})' for g in ['creative','argumentative']])
    sections += ['## 각 장르의 경험·행동 분포를 요약했다.', markdown(['평균(SD)', '창작', '논증'], descriptive)]
    def row(model, term):
        selected = models[(models.model == model) & (models.term == term)]
        if len(selected) != 1:
            raise ValueError(f'Expected one parameter row: {model}, {term}')
        return selected.iloc[0]
    focal = []
    for label, model, term, corrected in [
        ('H1: 개인 내 이해–소유감','primary_ordinal','understanding_w',False),
        ('개인 간 평균 이해–소유감','primary_ordinal','understanding_b',False),
        ('개인 내 인간 작성 비율(10%p)–소유감','primary_ordinal','human10_w',False),
        ('H2: 개인 내 이해–아이디어 도움','ideation_outcome','understanding_w',True),
        ('H3: 개인 내 이해×아이디어 도움–소유감','within_interaction','understanding_w:ideation_w',True)]:
        r = row(model, term)
        pv = r['p_holm_secondary'] if corrected else r['p']
        focal.append([label, f'{r.OR:.3f}', f'[{r.OR_low:.3f}, {r.OR_high:.3f}]', ('Holm ' if corrected else '') + pformat(pv)])
    sections += ['## 가설의 방향과 추정 불확실성을 함께 제시했다.', markdown(['관계','OR','95% CI','p'], focal)]
    sensitivities = []
    for model in ['primary_ordinal','equal_person_weight','session_order_adjusted','extended_behavior','ideation_adjusted','fluency_adjusted','all_queries_included','earliest_duplicate','creative','argumentative']:
        r = row(model, 'understanding_w')
        sensitivities.append([model, f'{r.OR:.3f}', f'[{r.OR_low:.3f}, {r.OR_high:.3f}]', pformat(r['p'])])
    sections += ['## 분석 사양에 따른 개인 내 이해–소유감 관계를 비교했다.', markdown(['모형','OR','95% CI','p(미보정)'], sensitivities)]
    qp = out / 'qualitative_audit.csv'
    if qp.exists():
        q = pd.read_csv(qp)
        rows = [[r.case_id,r.genre,int(r.understanding),int(r.ownership),int(r.ideation),f'{r.written_by_human:g}%',r.codes,r.paraphrase_ko,r.interpretive_limit] for r in q.itertuples()]
        sections += ['## 정성 사례는 대비 표집한 예비 해석이며 인간 검토가 남아 있다.', markdown(['사례','장르','U','O','I','H','예비 코드','한국어 요약','해석 한계'],rows)]
    else:
        sections += ['## 정성 결과는 이번 실행에서 포함하지 않았다.', '검증된 qualitative_audit.csv가 없어 기존 해석을 재사용하지 않았습니다.']
    (out / 'tables.md').write_text('\n\n'.join(sections) + '\n', encoding='utf-8')
    print(f'Wrote {out / "tables.md"}')


if __name__ == '__main__':
    main()
