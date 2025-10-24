## 许可证

本项目基于 [PDFMathTranslate-next](https://github.com/PDFMathTranslate/PDFMathTranslate-next) 和 [BabelDOC](https://github.com/funstory-ai/BabelDOC) 开发，遵循 GNU Affero 通用公共许可证版本 3 (AGPLv3) 发布。

**重要**: 根据 AGPLv3 要求，任何使用、修改或分发本软件的用户都必须：
1. 保持相同的开源许可
2. 向所有用户提供完整的源代码
3. 对于网络服务，需向用户提供获取相应源代码的方法

完整的许可证文本请见 [LICENSE](LICENSE) 文件。


## 项目版本
- pdf2zh Version: 2.6.4
- BabelDOC Version: 0.5.9

## 开源声明

本项目在产品中需显著声明其基于 PDFMathTranslate-next和 BabelDOC 开源项目，并遵循相应的开源协议进行开发和使用。同时，本项目也将允许开源。
本项目除celery部署外没有特别修改，有需要的也可直接到GitHub上看原始仓库代码。

## 主要特性

- 利用 Celery 分布式任务队列，提升翻译服务的可扩展性和稳定性。
- 支持多种 PDF 文档的翻译处理能力。
- 易于集成到现有产品或系统中。

##主要改动项
pdf2zh_next\high_level.py的_translate_in_subprocess，将其multiprocessing改为线程内直接调用，适配celery框架
babeldoc\format\pdf\document_il\backend\pdf_creater.py的subset_fonts_in_subprocess和save_pdf_with_timeout，同理将其multiprocessing改为线程内直接调用，适配celery框架
celery执行过程中会更新attachment表的文件状态，和celery客户端实现交互（可根据需要移除）

## 开源地址
项目源码及相关文档将在后续开源平台发布，敬请关注。