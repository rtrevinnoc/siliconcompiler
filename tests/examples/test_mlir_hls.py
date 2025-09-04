import os
import pytest


@pytest.mark.eda
@pytest.mark.ready
@pytest.mark.timeout(1200)
def test_py_mlir_hls():
    from mlir_hls import mlir_hls
    mlir_hls.main()

    assert os.path.isfile('build/mlir/job0/write.gds/0/outputs/main_kernel.gds')
