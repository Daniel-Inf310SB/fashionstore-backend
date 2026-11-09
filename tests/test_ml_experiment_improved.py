from app.services.ml.experiment import generate_synthetic_sales, run_demo, train_supervised


def test_temporal_split_and_baselines():
    df = generate_synthetic_sales()
    model, result = train_supervised(df)
    assert result['data_source'] == 'SYNTHETIC_DEMO'
    assert result['train_rows'] + result['test_rows'] == len(df)
    assert result['train_until'] < result['test_from']
    assert result['mae_bob'] < result['baseline_mae_bob']
    assert result['r2'] > 0
    assert 'trend' in model and 'residual_forest' in model


def test_reproducible_demo_and_kmeans_unchanged():
    first = run_demo(seed=2026)
    second = run_demo(seed=2026)
    assert first == second
    assert first['unsupervised']['n_products'] == 120
    assert first['unsupervised']['silhouette_score'] == 0.554
