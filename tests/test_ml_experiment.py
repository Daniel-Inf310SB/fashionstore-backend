import pytest

pytest.importorskip('numpy')
pytest.importorskip('pandas')
pytest.importorskip('sklearn')
from app.services.ml.experiment import (
    generate_synthetic_sales, train_supervised, synthetic_product_profiles,
    train_unsupervised, run_demo,
)


def test_sales_are_deterministic():
    a = generate_synthetic_sales(days=100, seed=14)
    b = generate_synthetic_sales(days=100, seed=14)
    assert a.equals(b)
    assert len(a) == 400
    assert a.sales_bob.min() >= 0


def test_supervised_split_is_chronological():
    _, results = train_supervised(generate_synthetic_sales(days=140))
    assert results['data_source'] == 'SYNTHETIC_DEMO'
    assert results['train_until'] < results['test_from']
    assert results['test_rows'] > 0
    assert results['mae_bob'] >= 0


def test_unsupervised_clusters_and_metric():
    _, results = train_unsupervised(synthetic_product_profiles())
    assert sum(results['cluster_sizes'].values()) == 120
    assert -1 <= results['silhouette_score'] <= 1


def test_no_real_data_claims():
    result = run_demo()
    assert 'SINTÉTICOS' in result['warning']
    assert result['supervised']['data_source'] == 'SYNTHETIC_DEMO'
    assert result['unsupervised']['data_source'] == 'SYNTHETIC_DEMO'
