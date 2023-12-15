from tempfile import NamedTemporaryFile

import pytest
from cocotb.runner import get_runner

from magia import Module, Input, Output
from magia.clock import clock


class TestSmokeCompile:
    TOP = "TopModule"

    def compile(self, module: Module):
        sv_code = Module.elaborate_all(module)
        sv_code = "\n".join(sv_code.values())

        with NamedTemporaryFile(mode="w", suffix=".sv") as f:
            print(sv_code)
            f.write(sv_code)
            f.flush()
            runner = get_runner("verilator")
            runner.build(
                verilog_sources=[f.name],
                hdl_toplevel=self.TOP,
                always=True,
            )

    @pytest.mark.parametrize("width", [8, 12, 16])
    def test_comb_operators(self, width):
        class TopModule(Module):
            def __init__(self, width, **kwargs):
                super().__init__(**kwargs)

                self.io += Input("a", width)
                self.io += Input("b", width)
                self.io += Output("q_accumulated", width)

                ops = [
                    self.io.a + self.io.b,
                    self.io.a - self.io.b,
                    self.io.a * self.io.b,
                    self.io.a & self.io.b,
                    self.io.a | self.io.b,
                    self.io.a ^ self.io.b,

                    self.io.a + 0x0F,
                    self.io.a - 0x0F,
                    self.io.a * 0x0F,
                    self.io.a & 0x0F,
                    self.io.a | 0x0F,
                    self.io.a ^ 0x0F,

                    self.io.a << 2,
                    self.io.a >> 2,
                ]

                for i, op in enumerate(ops):
                    self.io += Output(f"q_{i}", width)
                    self.io[f"q_{i}"] <<= op

                accumulator = self.io.a + self.io.b
                accumulator += self.io.a
                accumulator -= self.io.a
                accumulator *= self.io.a
                accumulator |= self.io.a
                accumulator &= self.io.a
                accumulator ^= self.io.a
                self.io.q_accumulated <<= accumulator

        self.compile(TopModule(width=width, name=self.TOP))

    @pytest.mark.parametrize("width", [8, 12, 16])
    def test_comb_registers(self, width):
        class TopModule(Module):
            def __init__(self, width, **kwargs):
                super().__init__(**kwargs)
                self.io += Input("clk", 1)
                self.io += Input("rst_n", 1)
                self.io += Input("reset", 1)
                self.io += Input("enable", 1)

                self.io += Input("a", width)
                self.io += Input("b", width)

                data = self.io.a + self.io.b

                # Generate all possible combinations of registers
                with clock(self.io.clk):
                    regs = [
                        data.reg(),
                        data.reg(reset=self.io.reset),
                        data.reg(reset=self.io.reset, reset_value=0xFF),
                        data.reg(async_reset=self.io.rst_n),
                        data.reg(async_reset=self.io.rst_n, async_reset_value=0xFF),
                        data.reg(
                            reset=self.io.reset, reset_value=0xFF,
                            async_reset=self.io.rst_n, async_reset_value=0xFF,
                        ),
                        # Repeat the above with enable
                        data.reg(enable=self.io.enable),
                        data.reg(reset=self.io.reset, enable=self.io.enable),
                        data.reg(reset=self.io.reset, reset_value=0xFF, enable=self.io.enable),
                        data.reg(async_reset=self.io.rst_n, enable=self.io.enable),
                        data.reg(
                            async_reset=self.io.rst_n, async_reset_value=0xFF,
                            enable=self.io.enable
                        ),
                        data.reg(
                            reset=self.io.reset, reset_value=0xFF,
                            async_reset=self.io.rst_n, async_reset_value=0xFF,
                            enable=self.io.enable,
                        ),
                    ]

                # Connect the Registers to output
                for i, reg in enumerate(regs):
                    self.io += Output(f"q_{i}", width)
                    self.io[f"q_{i}"] <<= reg

        self.compile(TopModule(width=width, name=self.TOP))