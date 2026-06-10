import json
from flask import Flask, render_template_string
from db import init_db, get_all_candidates

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bartender Recruitment</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; }
  header { background: #1a1d2e; border-bottom: 1px solid #2d3748; padding: 20px 32px; display: flex; align-items: center; gap: 12px; }
  header h1 { font-size: 1.4rem; font-weight: 600; }
  header span { font-size: 1.5rem; }
  .stats { display: flex; gap: 16px; padding: 24px 32px; flex-wrap: wrap; }
  .stat { background: #1a1d2e; border: 1px solid #2d3748; border-radius: 10px; padding: 16px 24px; min-width: 140px; }
  .stat .val { font-size: 2rem; font-weight: 700; color: #63b3ed; }
  .stat .lbl { font-size: 0.8rem; color: #718096; margin-top: 2px; }
  .table-wrap { padding: 0 32px 32px; overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; background: #1a1d2e; border-radius: 10px; overflow: hidden; }
  thead th { background: #2d3748; padding: 12px 16px; text-align: left; font-size: 0.8rem; text-transform: uppercase; letter-spacing: .05em; color: #a0aec0; }
  tbody tr { border-top: 1px solid #2d3748; transition: background .15s; }
  tbody tr:hover { background: #232639; }
  td { padding: 12px 16px; font-size: 0.9rem; vertical-align: middle; }
  .score-bar { display: flex; align-items: center; gap: 8px; }
  .bar-bg { background: #2d3748; border-radius: 4px; height: 6px; width: 80px; }
  .bar-fill { background: linear-gradient(90deg, #48bb78, #38a169); border-radius: 4px; height: 6px; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
  .badge-green { background: #1c4532; color: #68d391; }
  .badge-yellow { background: #744210; color: #f6e05e; }
  .badge-red { background: #742a2a; color: #fc8181; }
  .toggle-btn { background: none; border: 1px solid #4a5568; color: #a0aec0; padding: 4px 10px; border-radius: 6px; cursor: pointer; font-size: 0.78rem; }
  .toggle-btn:hover { background: #2d3748; color: #e2e8f0; }
  .detail-row td { padding: 0; }
  .detail-inner { padding: 16px 20px; background: #12151f; }
  .detail-inner h4 { font-size: 0.8rem; color: #718096; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 12px; }
  .qa-item { display: flex; gap: 10px; margin-bottom: 10px; padding: 10px 12px; border-radius: 8px; font-size: 0.85rem; }
  .qa-ok { background: #1c3a27; border-left: 3px solid #48bb78; }
  .qa-fail { background: #3a1c1c; border-left: 3px solid #fc8181; }
  .qa-item .icon { font-size: 1rem; flex-shrink: 0; }
  .qa-text { flex: 1; }
  .qa-text .question { color: #e2e8f0; margin-bottom: 4px; }
  .qa-text .ans { font-size: 0.8rem; color: #a0aec0; }
  .qa-text .hint { font-size: 0.78rem; color: #718096; margin-top: 4px; font-style: italic; }
  .empty { text-align: center; padding: 60px; color: #4a5568; }
</style>
</head>
<body>
<header><span>🍹</span><h1>Bartender Recruitment — London</h1></header>

<div class="stats">
  <div class="stat"><div class="val">{{ candidates|length }}</div><div class="lbl">Кандидатов</div></div>
  <div class="stat"><div class="val">{{ "%.0f"|format(avg_score) }}%</div><div class="lbl">Средний балл</div></div>
  <div class="stat"><div class="val">{{ top_count }}</div><div class="lbl">С результатом ≥70%</div></div>
</div>

<div class="table-wrap">
{% if candidates %}
<table>
  <thead>
    <tr>
      <th>#</th>
      <th>Имя</th>
      <th>Национальность</th>
      <th>Опыт</th>
      <th>Результат</th>
      <th>Рейтинг</th>
      <th>Дата</th>
      <th></th>
    </tr>
  </thead>
  <tbody>
  {% for c in candidates %}
  {% set answers = c.answers|fromjson %}
  {% set pct = (c.score / c.total * 100)|int %}
  <tr>
    <td style="color:#4a5568">{{ loop.index }}</td>
    <td><strong>{{ c.name }}</strong></td>
    <td>{{ c.nationality }}</td>
    <td>{{ c.experience }}</td>
    <td>
      <div class="score-bar">
        <div class="bar-bg"><div class="bar-fill" style="width:{{ pct }}%"></div></div>
        <span>{{ c.score }}/{{ c.total }}</span>
      </div>
    </td>
    <td>
      {% if pct >= 70 %}
        <span class="badge badge-green">{{ pct }}% ✓</span>
      {% elif pct >= 40 %}
        <span class="badge badge-yellow">{{ pct }}%</span>
      {% else %}
        <span class="badge badge-red">{{ pct }}%</span>
      {% endif %}
    </td>
    <td style="color:#718096;font-size:0.8rem">{{ c.created_at[:10] }}</td>
    <td><button class="toggle-btn" onclick="toggle('d{{ c.id }}')">Детали</button></td>
  </tr>
  <tr id="d{{ c.id }}" class="detail-row" style="display:none">
    <td colspan="8">
      <div class="detail-inner">
        <h4>Ответы кандидата</h4>
        {% for a in answers %}
        <div class="qa-item {{ 'qa-ok' if a.is_correct else 'qa-fail' }}">
          <div class="icon">{{ '✅' if a.is_correct else '❌' }}</div>
          <div class="qa-text">
            <div class="question">{{ loop.index }}. {{ a.q }}</div>
            <div class="ans">
              {% if not a.is_correct %}
                Ответил: <strong>{{ a.your }}</strong> · Правильно: <strong>{{ a.correct }}</strong>
              {% else %}
                Ответ: <strong>{{ a.your }}</strong> — верно
              {% endif %}
            </div>
            {% if not a.is_correct %}<div class="hint">{{ a.hint }}</div>{% endif %}
          </div>
        </div>
        {% endfor %}
      </div>
    </td>
  </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
<div class="empty">Пока нет кандидатов. Ждём первых ответов от бота.</div>
{% endif %}
</div>

<script>
function toggle(id) {
  const row = document.getElementById(id);
  row.style.display = row.style.display === 'none' ? 'table-row' : 'none';
}
</script>
</body>
</html>
"""


@app.template_filter("fromjson")
def fromjson(s):
    return json.loads(s) if s else []


@app.route("/")
def index():
    init_db()
    rows = get_all_candidates()
    candidates = [dict(r) for r in rows]
    avg = (sum(c["score"] / c["total"] * 100 for c in candidates) / len(candidates)) if candidates else 0
    top = sum(1 for c in candidates if c["score"] / c["total"] >= 0.7)
    return render_template_string(HTML, candidates=candidates, avg_score=avg, top_count=top)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
