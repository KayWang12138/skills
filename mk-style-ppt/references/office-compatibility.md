# Office 兼容性与修复

适用于所有最终 PPTX，尤其是原生对象移植、多次增量编辑和直接修改 OOXML 的文件。

## 不把渲染成功当作兼容性证明

宽松的读取器可能忽略非法节点顺序，Office 则可能触发修复并删除整页。ZIP 完整、XML 可解析、幻灯片能渲染、生成工具能导入，都不能单独证明 Office 兼容。

优先使用制作工具的原生对象操作。确需移植 XML 时保持元素在父节点中的合法位置，不要移除后直接追加到父节点末尾。

## 已发生的结构错误

`p:cSld` 的子节点顺序为：

```text
bg? → spTree → custDataLst? → controls? → extLst?
```

其中 `spTree` 必须存在。错误的 `bg, extLst, spTree` 可以正常渲染，却会导致 Office 修复时丢弃页面。替换 `spTree` 时保持原位置，或按上述序列插入。规则依据 [Microsoft CommonSlideData 文档](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.presentation.commonslidedata) 和 [官方 Open XML SDK schema](https://github.com/dotnet/Open-XML-SDK/blob/main/data/schemas/schemas_openxmlformats_org_presentationml_2006_main.json)。

## 交付检查

运行：

```text
python scripts/check_pptx_structure.py path/to/final.pptx
```

检查器只读，覆盖已知的节点顺序、关系目标、关系引用和页面对象 ID 问题。它不是完整 ECMA-376 / ISO 29500 schema 验证器，也不验证外观、公式或 Office 实际打开结果。

此外仍需：

- 完成制作工具的包完整性、布局、字体、图表和可编辑性验证。
- 如有完整 schema 验证能力，运行 schema 验证，不只检查 XML 语法。
- 有 Office 时，在副本上实际打开，确认没有修复提示、页数不变、图片与可编辑对象仍在。不要覆盖用户已打开的文件或把自动修复后删页的文件当完成品。
- 无 Office 时，不声称“已在 Office 验证”，明确已完成结构与渲染检查及剩余验证范围。

## 修复流程

定位错误节点或引用，制作新副本，尽量只修复结构。修复后比较文字、图形树、表格、图表、嵌入工作簿、图片与总页数，未涉及的部件应保持不变。重新渲染受影响页面，并扫描其他页面是否意外变化。

说明具体原因与验证范围，不把自身生成的结构错误笼统归为“Office 版本不兼容”。发现生成流程会重复引入错误时，修正相应构建逻辑。
