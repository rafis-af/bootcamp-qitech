"""Os testes deste pacote chamam funções de src/ direto, sem HTTP.

Só fazem isso onde a rota não tem como produzir o erro: pool esgotado, banco
fora do ar, timeout de consulta e outros que dependem de infraestrutura. Eles
precisam achar o pacote `src` (`errors`, `connectors`...). Na imagem de testes
do Docker ele fica em /app; na sua máquina, em ../src.
"""
import sys
from pathlib import Path

SRC_CANDIDATES = [Path("/app"), Path(__file__).resolve().parents[2] / "src"]

for candidate in SRC_CANDIDATES:
    if (candidate / "errors").is_dir():
        sys.path.insert(0, str(candidate))
        break
