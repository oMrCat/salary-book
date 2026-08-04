package com.salarybook.app.sync

import org.w3c.dom.Document
import org.w3c.dom.Element
import java.io.InputStream
import java.io.OutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream
import java.util.zip.ZipOutputStream
import javax.xml.parsers.DocumentBuilderFactory

/**
 * 极简 .xlsx 读写（不依赖第三方库）。
 * 写：inline 字符串单元格；读：兼容 inlineStr / sharedStrings / 数值。
 */
object Xlsx {

    private fun esc(s: String): String = s
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
        .replace("'", "&apos;")

    fun write(out: OutputStream, sheets: List<Pair<String, List<List<Any>>>>) {
        ZipOutputStream(out).use { zip ->
            zip.putNextEntry(ZipEntry("[Content_Types].xml"))
            zip.write(contentTypes(sheets.size).toByteArray(Charsets.UTF_8))
            zip.closeEntry()
            zip.putNextEntry(ZipEntry("_rels/.rels"))
            zip.write(relsXml().toByteArray(Charsets.UTF_8))
            zip.closeEntry()
            zip.putNextEntry(ZipEntry("xl/workbook.xml"))
            zip.write(workbookXml(sheets.map { it.first }).toByteArray(Charsets.UTF_8))
            zip.closeEntry()
            zip.putNextEntry(ZipEntry("xl/_rels/workbook.xml.rels"))
            zip.write(workbookRels(sheets.size).toByteArray(Charsets.UTF_8))
            zip.closeEntry()
            sheets.forEachIndexed { i, (_, rows) ->
                zip.putNextEntry(ZipEntry("xl/worksheets/sheet${i + 1}.xml"))
                zip.write(sheetXml(rows).toByteArray(Charsets.UTF_8))
                zip.closeEntry()
            }
        }
    }

    private fun contentTypes(n: Int): String {
        val sb = StringBuilder()
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
        sb.append("<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">")
        sb.append("<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>")
        sb.append("<Default Extension=\"xml\" ContentType=\"application/xml\"/>")
        sb.append("<Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>")
        for (i in 1..n) {
            sb.append("<Override PartName=\"/xl/worksheets/sheet$i.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>")
        }
        sb.append("</Types>")
        return sb.toString()
    }

    private fun relsXml(): String =
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>" +
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">" +
            "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/>" +
            "</Relationships>"

    private fun workbookXml(names: List<String>): String {
        val sb = StringBuilder()
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
        sb.append("<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"><sheets>")
        names.forEachIndexed { i, name ->
            sb.append("<sheet name=\"${esc(name)}\" sheetId=\"${i + 1}\" r:id=\"rId${i + 1}\"/>")
        }
        sb.append("</sheets></workbook>")
        return sb.toString()
    }

    private fun workbookRels(n: Int): String {
        val sb = StringBuilder()
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
        sb.append("<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">")
        for (i in 1..n) {
            sb.append("<Relationship Id=\"rId$i\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet$i.xml\"/>")
        }
        sb.append("</Relationships>")
        return sb.toString()
    }

    private fun sheetXml(rows: List<List<Any>>): String {
        val sb = StringBuilder()
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
        sb.append("<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><sheetData>")
        rows.forEachIndexed { ri, row ->
            sb.append("<row r=\"${ri + 1}\">")
            row.forEachIndexed { ci, value ->
                val ref = colName(ci) + (ri + 1)
                when (value) {
                    is Number -> sb.append("<c r=\"$ref\"><v>$value</v></c>")
                    else -> sb.append("<c r=\"$ref\" t=\"inlineStr\"><is><t>${esc(value.toString())}</t></is></c>")
                }
            }
            sb.append("</row>")
        }
        sb.append("</sheetData></worksheet>")
        return sb.toString()
    }

    private fun colName(index: Int): String {
        val sb = StringBuilder()
        var i = index + 1
        while (i > 0) {
            i--
            sb.insert(0, ('A'.code + i % 26).toChar())
            i /= 26
        }
        return sb.toString()
    }

    // ---------- 读取 ----------
    data class Row(val number: Int, val cells: List<String>)

    data class Sheet(val name: String, val rows: List<Row>)

    fun read(input: InputStream): List<Sheet> {
        val entries = HashMap<String, ByteArray>()
        ZipInputStream(input).use { zip ->
            var e = zip.nextEntry
            while (e != null) {
                if (!e.isDirectory) {
                    entries[e.name] = zip.readBytes()
                }
                zip.closeEntry()
                e = zip.nextEntry
            }
        }
        val factory = DocumentBuilderFactory.newInstance()
        val builder = factory.newDocumentBuilder()

        val wbBytes = entries["xl/workbook.xml"] ?: throw IllegalArgumentException("不是有效的 Excel 文件")
        val wbDoc = builder.parse(wbBytes.inputStream())
        val sheetNames = ArrayList<String>()
        val wbNodes = wbDoc.documentElement.getElementsByTagName("sheet")
        for (i in 0 until wbNodes.length) {
            sheetNames.add((wbNodes.item(i) as Element).getAttribute("name"))
        }

        val shared = parseSharedStrings(entries["xl/sharedStrings.xml"], builder)

        val relMap = HashMap<String, String>()
        entries["xl/_rels/workbook.xml.rels"]?.let {
            val relDoc = builder.parse(it.inputStream())
            val relNodes = relDoc.documentElement.getElementsByTagName("Relationship")
            for (i in 0 until relNodes.length) {
                val el = relNodes.item(i) as Element
                relMap[el.getAttribute("Id")] = el.getAttribute("Target").removePrefix("/")
            }
        }

        val sheets = ArrayList<Sheet>()
        for (i in sheetNames.indices) {
            val relTarget = relMap["rId${i + 1}"]
            val file = relTarget ?: "xl/worksheets/sheet${i + 1}.xml"
            val xml = entries[file] ?: entries["xl/$file"] ?: continue
            sheets.add(Sheet(sheetNames[i], parseSheet(builder.parse(xml.inputStream()), shared)))
        }
        return sheets
    }

    private fun parseSharedStrings(bytes: ByteArray?, builder: javax.xml.parsers.DocumentBuilder): List<String> {
        val out = ArrayList<String>()
        if (bytes == null) return out
        try {
            val doc = builder.parse(bytes.inputStream())
            val siNodes = doc.documentElement.getElementsByTagName("si")
            for (i in 0 until siNodes.length) {
                val si = siNodes.item(i) as Element
                val tNodes = si.getElementsByTagName("t")
                val sb = StringBuilder()
                for (j in 0 until tNodes.length) sb.append(tNodes.item(j).textContent)
                out.add(sb.toString())
            }
        } catch (_: Exception) {
        }
        return out
    }

    private fun parseSheet(doc: Document, shared: List<String>): List<Row> {
        val rows = ArrayList<Row>()
        val rowNodes = doc.documentElement.getElementsByTagName("row")
        for (i in 0 until rowNodes.length) {
            val rowEl = rowNodes.item(i) as Element
            val num = rowEl.getAttribute("r").toIntOrNull() ?: (i + 1)
            val cols = ArrayList<String>()
            val cellNodes = rowEl.getElementsByTagName("c")
            for (j in 0 until cellNodes.length) {
                val cell = cellNodes.item(j) as Element
                val t = cell.getAttribute("t")
                val text = when (t) {
                    "inlineStr" -> {
                        val isEls = cell.getElementsByTagName("t")
                        if (isEls.length > 0) isEls.item(0).textContent else ""
                    }
                    "s" -> {
                        val vEls = cell.getElementsByTagName("v")
                        if (vEls.length > 0) {
                            val idx = vEls.item(0).textContent.trim().toIntOrNull() ?: -1
                            if (idx in shared.indices) shared[idx] else ""
                        } else ""
                    }
                    else -> {
                        val vEls = cell.getElementsByTagName("v")
                        if (vEls.length > 0) vEls.item(0).textContent else ""
                    }
                }
                cols.add(text)
            }
            rows.add(Row(num, cols))
        }
        return rows
    }
}
