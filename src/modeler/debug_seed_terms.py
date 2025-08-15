import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modeler.search_tools import get_seed_terms

# Get all terms
result = get_seed_terms('https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01', k=1000)
print(f'Total unique terms: {len(result)}')

total_freq = sum(r['frequency'] for r in result)
print(f'Total frequency: {total_freq}')

total_raw_count = sum(r['raw_count'] for r in result)
print(f'Total raw count: {total_raw_count}')

print(f'\nFirst 10 terms:')
for i, term in enumerate(result[:10]):
    print(f'{i+1}. {term["term"]} - freq: {term["frequency"]:.6f}, count: {term["raw_count"]}')
