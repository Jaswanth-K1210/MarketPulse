"""Check what alerts are in the database"""

from app.services.database import database

alerts = database.get_all_alerts()
articles = database.get_all_articles()

print(f'\n{"="*80}')
print(f'  DATABASE STATUS')
print(f'{"="*80}\n')

print(f'📄 Articles: {len(articles)}')
print(f'🚨 Alerts: {len(alerts)}')
print()

if alerts:
    print(f'{"="*80}')
    print('  RECENT ALERTS')
    print(f'{"="*80}\n')

    for i, alert in enumerate(alerts[-3:], 1):
        print(f'\n{"-"*80}')
        print(f'ALERT #{i}: {alert.id[:8]}...')
        print(f'{"-"*80}')
        print(f'Type: {alert.type}')
        print(f'Severity: {alert.severity}')
        print(f'Impact: {alert.impact_percent:+.2f}%')
        print(f'Dollar Impact: ${alert.impact_dollar:,.2f}')
        print(f'Recommendation: {alert.recommendation}')
        print(f'Confidence: {alert.confidence:.0%}')
        print(f'\nAffected Holdings:')
        for holding in alert.affected_holdings:
            print(f'  • {holding.company} ({holding.ticker})')
            print(f'    Impact: {holding.impact_percent:+.1f}% = ${holding.impact_dollar:,.2f}')
            print(f'    Position: {holding.quantity} shares @ ${holding.current_price:.2f}')
        print(f'\nExplanation:')
        print(f'  {alert.explanation}')
        print(f'\nCreated: {alert.created_at}')

print(f'\n{"="*80}\n')

if alerts:
    print(f'✅ SUCCESS! Gemini is generating alerts from short Finnhub summaries!')
else:
    print(f'⚠️  No alerts yet - keep testing with more articles')
