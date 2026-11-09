"""Experimentos académicos con datos SINTÉTICOS, nunca métricas reales del tenant.

Sin conexiones SQL, sin datos personales y sin escribir en PostgreSQL.
Las predicciones son demostrativas; no deben presentarse como pronósticos reales.
"""
from __future__ import annotations

from datetime import date, timedelta
from math import pi, sin


def generate_synthetic_sales(*, days: int = 450, branches: int = 4, seed: int = 2026):
    import numpy as np
    import pandas as pd

    if days < 90 or not 2 <= branches <= 20:
        raise ValueError('Se requieren >=90 días y entre 2 y 20 sucursales sintéticas.')
    rng = np.random.default_rng(seed)
    start = date(2024, 1, 1)
    records = []
    for i in range(days):
        d = start + timedelta(days=i)
        for branch in range(branches):
            weekday = d.weekday()
            promo = int(rng.random() < 0.18)
            seasonal = 1 + 0.13 * sin(2*pi*i/365)
            expected = (155 + 19*branch + (32 if weekday >= 5 else 0) + 42*promo + .075*i)*seasonal
            sales = max(0, expected + rng.normal(0, 19))
            records.append({'date': d, 'day_index': i, 'branch_index': branch,
                            'weekday': weekday, 'month': d.month, 'is_weekend': int(weekday>=5),
                            'promotion': promo, 'sales_bob': round(float(sales), 2)})
    return pd.DataFrame(records)


def _trend_features(df):
    """Variables conocidas antes de la venta; no utiliza sales_bob ni datos futuros."""
    import numpy as np

    day = df['day_index'].to_numpy(dtype=float)
    season_sin = np.sin(2 * np.pi * day / 365)
    season_cos = np.cos(2 * np.pi * day / 365)
    branch = df['branch_index'].to_numpy(dtype=float)
    weekend = df['is_weekend'].to_numpy(dtype=float)
    promotion = df['promotion'].to_numpy(dtype=float)
    return np.column_stack((day, branch, weekend, promotion, season_sin,
                            season_cos, day * season_sin, day * season_cos,
                            branch * season_sin, weekend * season_sin,
                            promotion * season_sin))


def train_supervised(df):
    """Evaluación temporal sin fuga de datos: tendencia + RF sobre residuos.

    Random Forest puro no extrapola tendencias crecientes; la regresión lineal
    explica la tendencia y el bosque modela solo los residuos. Los modelos se
    entrenan exclusivamente sobre el 80 % inicial de los días.
    """
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    required = {'date', 'day_index', 'branch_index', 'weekday', 'is_weekend',
                'promotion', 'sales_bob'}
    if missing := required.difference(df.columns):
        raise ValueError(f'Faltan columnas para entrenamiento: {sorted(missing)}')
    days = sorted(df['day_index'].unique())
    if len(days) < 90:
        raise ValueError('Historial insuficiente para una evaluación temporal.')
    cut = days[int(len(days) * .8)]
    train = df.loc[df.day_index < cut]
    test = df.loc[df.day_index >= cut]
    if train.empty or test.empty:
        raise ValueError('La división cronológica no generó ambos conjuntos.')

    x_train = _trend_features(train)
    x_test = _trend_features(test)
    trend = LinearRegression().fit(x_train, train.sales_bob)
    trend_train = trend.predict(x_train)
    trend_test = trend.predict(x_test)
    residual_features = ['branch_index', 'weekday', 'is_weekend', 'promotion', 'month']
    # Mes y día de semana son conocidos a priori; no se utilizan ventas futuras.
    model = RandomForestRegressor(n_estimators=110, min_samples_leaf=3,
                                  random_state=2026, n_jobs=1)
    model.fit(train[residual_features], train.sales_bob.to_numpy() - trend_train)
    predicted = trend_test + model.predict(test[residual_features])
    baseline = np.full(len(test), float(train.sales_bob.mean()))
    mae = float(mean_absolute_error(test.sales_bob, predicted))
    trend_mae = float(mean_absolute_error(test.sales_bob, trend_test))
    result = {
        'data_source': 'SYNTHETIC_DEMO',
        'algorithm': 'LinearRegression + RandomForestRegressor (residuos)',
        'train_rows': int(len(train)), 'test_rows': int(len(test)),
        'train_until': str(max(train.date)), 'test_from': str(min(test.date)),
        'mae_bob': round(mae, 3),
        'rmse_bob': round(float(np.sqrt(mean_squared_error(test.sales_bob, predicted))), 3),
        'r2': round(float(r2_score(test.sales_bob, predicted)), 4),
        'baseline_mae_bob': round(float(mean_absolute_error(test.sales_bob, baseline)), 3),
        'linear_trend_mae_bob': round(trend_mae, 3),
        'beats_mean_baseline': mae < float(mean_absolute_error(test.sales_bob, baseline)),
        'beats_linear_trend': mae < trend_mae,
        'note': ('Evaluación cronológica sobre datos sintéticos. El bosque aprende residuos '
                 'tras retirar la tendencia lineal; comparar también con tendencia lineal '
                 'evita atribuir toda la mejora al bosque. No es pronóstico comercial.'),
    }
    return {'trend': trend, 'residual_forest': model}, result


def synthetic_product_profiles(*, products: int = 120, seed: int = 2026):
    import numpy as np
    import pandas as pd

    if products < 12:
        raise ValueError('Se requieren al menos 12 productos sintéticos.')
    rng = np.random.default_rng(seed)
    groups = rng.choice(3, size=products)
    units = np.maximum(0, rng.normal(np.choose(groups, [9, 42, 85]), 8)).round().astype(int)
    stock = np.maximum(0, rng.normal(np.choose(groups, [140, 78, 25]), 14)).round().astype(int)
    prices = rng.uniform(65, 390, products).round(2)
    return pd.DataFrame({'product_demo_id': range(1, products+1),
                         'units_sold': units, 'available_stock': stock,
                         'revenue_bob': (units*prices).round(2)})


def train_unsupervised(df):
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    features = ['units_sold', 'available_stock', 'revenue_bob']
    if len(df) < 12:
        raise ValueError('Se requieren al menos 12 observaciones.')
    x = df[features]
    pipeline = make_pipeline(StandardScaler(), KMeans(n_clusters=3, n_init=10, random_state=2026))
    clusters = pipeline.fit_predict(x)
    transformed = pipeline.named_steps['standardscaler'].transform(x)
    sizes = {str(i): int(np.sum(clusters == i)) for i in range(3)}
    if min(sizes.values()) < 2:
        raise ValueError('La segmentación no permite una evaluación estable.')
    score = float(silhouette_score(transformed, clusters))
    # Perfiles descriptivos: las etiquetas numéricas dependen del entrenamiento.
    profiles = []
    for cluster_id in range(3):
        rows = df.loc[clusters == cluster_id]
        profiles.append({
            'cluster_id': cluster_id,
            'products': int(len(rows)),
            'average_units_sold': round(float(rows['units_sold'].mean()), 2),
            'average_available_stock': round(float(rows['available_stock'].mean()), 2),
            'average_revenue_bob': round(float(rows['revenue_bob'].mean()), 2),
        })
    # Denominación relativa basada en rotación; no constituye diagnóstico real.
    by_rotation = sorted(profiles, key=lambda item: item['average_units_sold'])
    for label, profile in zip(('ROTACION_BAJA', 'ROTACION_MEDIA', 'ROTACION_ALTA'), by_rotation):
        profile['relative_segment'] = label
    profiles.sort(key=lambda item: item['cluster_id'])
    return pipeline, {'data_source': 'SYNTHETIC_DEMO', 'algorithm': 'KMeans',
                      'n_products': len(df), 'clusters': 3, 'cluster_sizes': sizes,
                      'silhouette_score': round(score, 4),
                      'profiles': profiles,
                      'note': 'Las etiquetas 0, 1 y 2 no tienen significado comercial fijo.'}


def run_demo(*, seed: int = 2026):
    sales = generate_synthetic_sales(seed=seed)
    _, supervised = train_supervised(sales)
    products = synthetic_product_profiles(seed=seed)
    _, unsupervised = train_unsupervised(products)
    return {'warning': 'RESULTADOS SINTÉTICOS DE DEMOSTRACIÓN: NO SON PREDICCIONES NI VENTAS REALES',
            'seed': seed, 'supervised': supervised, 'unsupervised': unsupervised}
