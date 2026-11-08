# Yayın rehberi (PyPI)

Bu adımlar senin PyPI hesabınla yapılır; paketi hazırladım ama yükleme için hesap/token gerekiyor.

## 0. Yayından önce

1. **Paket adının boş olduğunu kontrol et:** https://pypi.org/project/asciireveal/ adresi 404 veriyorsa ad boştur.
   Doluysa `pyproject.toml` içindeki `name` alanını (ve istersen `src/asciireveal` klasörünü) değiştir.
2. `LICENSE` dosyasındaki ve `pyproject.toml` içindeki `authors` alanındaki "asciireveal contributors"
   yerine kendi adını yaz.
3. İstersen `pyproject.toml` içine `[project.urls]` ekle (GitHub deposu, vb.).

## 1. Derle ve kontrol et

```bash
pip install -e ".[dev]"
pytest
python -m build            # dist/ altında .whl ve .tar.gz üretir
twine check dist/*
```

## 2. Önce TestPyPI'da dene

1. https://test.pypi.org adresinde hesap aç, **Account settings → API tokens** altından token üret.
2. Yükle:
   ```bash
   twine upload --repository testpypi dist/*
   # kullanıcı adı: __token__   şifre: pypi-... (token)
   ```
3. Temiz bir ortamda dene:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple asciireveal
   asciireveal --version
   ```

## 3. Gerçek PyPI

https://pypi.org üzerinde hesap + token aç, sonra:

```bash
twine upload dist/*
```

PyPI'da aynı sürüm numarası ikinci kez yüklenemez; her yayın için `pyproject.toml` ve
`src/asciireveal/__init__.py` içindeki sürümü birlikte artır.

## Öneri: GitHub Actions ile otomatik yayın

PyPI'da "Trusted Publisher" tanımlarsan token saklamadan, GitHub'da bir sürüm (release)
oluşturduğunda otomatik yayınlanır: https://docs.pypi.org/trusted-publishers/
