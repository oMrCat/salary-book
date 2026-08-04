# -*- coding: utf-8 -*-
"""打工人工资记录与对账软件 入口。"""

import sys

from salary_app.ui import SalaryApp


def main():
    app = SalaryApp()
    app.mainloop()


if __name__ == "__main__":
    sys.exit(main())
