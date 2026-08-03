/**
 * dor-edit — סרגל אישור/דחייה פר-שינוי בתוך Google Docs.
 *
 * מותאם מ-~/Developer/google-docs-mcp/apps-script-sidebar.js (בלי אימוג'ים).
 * משלים את upload_to_gdocs.py --propose: הסקריפט צובע visual-diff (ירוק+underline
 * לתוספת, אדום+strikethrough לישן), והסרגל הזה נותן לדור לאשר או לדחות **כל שינוי
 * בנפרד** בתוך Docs — במקום --resolve הגלובלי (accept/reject על כל המסמך בבת אחת).
 *
 * התקנה חד-פעמית: במסמך, Extensions, Apps Script, הדבק את כל הקובץ, Save,
 * חזרה למסמך, תפריט "עורך רוח", "ניהול שינויים (סרגל צד)".
 *
 * הלוגיקה (getEditsList/resolveEdit) מזהה את אותם סימונים ש---propose כותב:
 * inserted = underline + ירוק ובלי strikethrough; deleted = strikethrough.
 * accept פר-שינוי: מוחק את הישן, מנקה עיצוב מהחדש. reject: מוחק את החדש, מחזיר את הישן.
 */

function onOpen() {
  DocumentApp.getUi()
      .createMenu('עורך רוח')
      .addItem('ניהול שינויים (סרגל צד)', 'showSidebar')
      .addToUi();
}

function showSidebar() {
  var htmlContent = `
    <!DOCTYPE html>
    <html>
      <head>
        <base target="_top">
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            padding: 15px;
            margin: 0;
            color: #3c4043;
            direction: rtl;
            background-color: #f8f9fa;
          }
          .header {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 15px;
            border-bottom: 1px solid #dadce0;
            padding-bottom: 10px;
            color: #1a73e8;
          }
          .btn-refresh {
            background-color: #1a73e8;
            color: white;
            width: 100%;
            margin-bottom: 15px;
            padding: 8px 12px;
            font-size: 13px;
            font-weight: 500;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15);
          }
          .btn-refresh:hover {
            background-color: #1557b0;
          }
          .edit-item {
            border: 1px solid #dadce0;
            padding: 12px;
            margin-bottom: 12px;
            border-radius: 8px;
            background: white;
            box-shadow: 0 1px 2px 0 rgba(60,64,67,0.1);
            transition: all 0.2s ease;
          }
          .edit-item:hover {
            box-shadow: 0 1px 3px 1px rgba(60,64,67,0.2);
            border-color: #1a73e8;
          }
          .original {
            color: #c5221f;
            text-decoration: line-through;
            background-color: #fce8e6;
            padding: 1px 4px;
            border-radius: 3px;
          }
          .replacement {
            color: #137333;
            background-color: #e6f4ea;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 500;
          }
          .btn-group {
            margin-top: 10px;
            display: flex;
            gap: 8px;
          }
          button.action {
            padding: 6px 12px;
            border: 1px solid #dadce0;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            flex: 1;
            transition: background-color 0.15s;
          }
          .btn-accept {
            background-color: #e6f4ea;
            color: #137333;
            border-color: #ceead6 !important;
          }
          .btn-accept:hover {
            background-color: #d2e7d6;
          }
          .btn-reject {
            background-color: #fce8e6;
            color: #c5221f;
            border-color: #fad2cf !important;
          }
          .btn-reject:hover {
            background-color: #f7c5c0;
          }
          .no-edits {
            text-align: center;
            color: #5f6368;
            margin-top: 30px;
            font-size: 13px;
          }
          .edit-type {
            font-size: 10px;
            text-transform: uppercase;
            font-weight: bold;
            color: #70757a;
            margin-bottom: 6px;
          }
        </style>
      </head>
      <body>
        <div class="header">הצעות עריכה של עורך רוח</div>
        <button class="btn-refresh" onclick="loadEdits()">רענן הצעות</button>
        <div id="edits-list">טוען...</div>

        <script>
          function loadEdits() {
            document.getElementById('edits-list').innerHTML = '<div class="no-edits">טוען הצעות עריכה מהמסמך...</div>';
            google.script.run.withSuccessHandler(renderEdits).getEditsList();
          }

          function renderEdits(edits) {
            var listDiv = document.getElementById('edits-list');
            if (!edits || edits.length === 0) {
              listDiv.innerHTML = '<div class="no-edits">לא נמצאו הצעות עריכה במסמך.</div>';
              return;
            }

            var html = '';
            edits.forEach(function(edit, idx) {
              html += '<div class="edit-item" onclick="selectEdit(' + edit.startIndex + ')">';

              if (edit.type === 'replace') {
                html += '<div class="edit-type">החלפת טקסט</div>';
                html += '<div>שנה את <span class="original">' + escapeHtml(edit.originalText) + '</span> ל-<span class="replacement">' + escapeHtml(edit.newText) + '</span></div>';
              } else if (edit.type === 'delete') {
                html += '<div class="edit-type">מחיקת טקסט</div>';
                html += '<div>מחק את <span class="original">' + escapeHtml(edit.originalText) + '</span></div>';
              } else if (edit.type === 'insert') {
                html += '<div class="edit-type">הוספת טקסט</div>';
                html += '<div>הוסף את <span class="replacement">' + escapeHtml(edit.newText) + '</span></div>';
              }

              html += '<div class="btn-group">';
              html += '<button class="action btn-accept" onclick="event.stopPropagation(); acceptEdit(' + idx + ')">אשר</button>';
              html += '<button class="action btn-reject" onclick="event.stopPropagation(); rejectEdit(' + idx + ')">דחה</button>';
              html += '</div>';
              html += '</div>';
            });
            listDiv.innerHTML = html;
          }

          function selectEdit(startIndex) {
            google.script.run.selectDocumentIndex(startIndex);
          }

          function acceptEdit(idx) {
            google.script.run.withSuccessHandler(loadEdits).resolveEdit(idx, 'accept');
          }

          function rejectEdit(idx) {
            google.script.run.withSuccessHandler(loadEdits).resolveEdit(idx, 'reject');
          }

          function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
          }

          // טעינה ראשונית
          loadEdits();
        </script>
      </body>
    </html>
  `;
  var html = HtmlService.createHtmlOutput(htmlContent)
      .setTitle('ניהול שינויים של עורך רוח')
      .setWidth(300);
  DocumentApp.getUi().showSidebar(html);
}

function selectDocumentIndex(targetIndex) {
  var doc = DocumentApp.getActiveDocument();
  var body = doc.getBody();
  var currentIdx = 0;

  function traverse(element) {
    var type = element.getType();
    if (type === DocumentApp.ElementType.TEXT) {
      var text = element.asText().getText();
      var len = text.length;
      if (targetIndex >= currentIdx && targetIndex < currentIdx + len) {
        var offset = targetIndex - currentIdx;
        var position = doc.newPosition(element, offset);
        doc.setCursor(position);

        // גלילה למיקום דרך הגדרת הטווח הפעיל
        var rangeBuilder = doc.newRange();
        rangeBuilder.addElement(element, offset, Math.min(offset + 1, len - 1));
        doc.setActiveRange(rangeBuilder.build());

        return true;
      }
      currentIdx += len;
    } else if (element.getNumChildren) {
      for (var i = 0; i < element.getNumChildren(); i++) {
        if (traverse(element.getChild(i))) return true;
      }
    }
    return false;
  }

  traverse(body);
}

function getEditsList() {
  var doc = DocumentApp.getActiveDocument();
  var body = doc.getBody();
  var edits = [];
  var state = { currentIdx: 0 };

  var numChildren = body.getNumChildren();
  for (var i = 0; i < numChildren; i++) {
    var child = body.getChild(i);
    findEditsInElement(child, edits, state);
  }

  edits.sort(function(a, b) {
    return a.position - b.position;
  });

  var groupedEdits = [];
  var i = 0;
  while (i < edits.length) {
    var current = edits[i];
    var next = (i + 1 < edits.length) ? edits[i + 1] : null;

    if (next && current.type === 'deleted' && next.type === 'inserted' &&
        current.element.equals(next.element) && current.endOffset + 1 === next.startOffset) {
      groupedEdits.push({
        type: 'replace',
        originalText: current.text,
        newText: next.text,
        startIndex: current.startIndex,
        deletePart: current,
        insertPart: next
      });
      i += 2;
    } else {
      groupedEdits.push({
        type: current.type === 'deleted' ? 'delete' : 'insert',
        originalText: current.type === 'deleted' ? current.text : '',
        newText: current.type === 'inserted' ? current.text : '',
        startIndex: current.startIndex,
        deletePart: current.type === 'deleted' ? current : null,
        insertPart: current.type === 'inserted' ? current : null
      });
      i++;
    }
  }

  return groupedEdits;
}

function findEditsInElement(element, edits, state) {
  var type = element.getType();
  if (type === DocumentApp.ElementType.TEXT) {
    var textObj = element.asText();
    var text = textObj.getText();
    var elementStartIdx = state.currentIdx;

    var inInserted = false;
    var inDeleted = false;
    var currentStart = 0;

    for (var i = 0; i < text.length; i++) {
      var isStrikethrough = textObj.isStrikethrough(i);
      var isUnderline = textObj.isUnderline(i);
      var color = textObj.getForegroundColor(i);

      // זיהוי ירוק חסין: פרסור ה-hex ל-RGB ובדיקה שהירוק דומיננטי אמיתי.
      // --propose כותב ירוק #1a801a (r=26 g=128 b=26) ואדום #cc1a1a (r=204 g=26 b=26),
      // אומת מול documents.get 17.07.2026. getForegroundColor(offset) מחזיר null אם
      // הצבע לא אחיד בטווח (או לא הוגדר) — ה-guard על color מטפל בכך.
      var isGreen = false;
      if (color) {
        var hex = color.toLowerCase();
        if (hex.charAt(0) === '#' && hex.length === 7) {
          var r = parseInt(hex.substr(1, 2), 16);
          var g = parseInt(hex.substr(3, 2), 16);
          var b = parseInt(hex.substr(5, 2), 16);
          isGreen = (g > r && g > b && g >= 80);  // ירוק דומיננטי; אדום/שחור/כחול נדחים
        }
      }

      var charInserted = (isUnderline && isGreen && !isStrikethrough);
      var charDeleted = isStrikethrough;

      if (charInserted) {
        if (inDeleted) {
          edits.push({ type: 'deleted', text: text.substring(currentStart, i), element: textObj, startOffset: currentStart, endOffset: i - 1, position: elementStartIdx + currentStart, startIndex: elementStartIdx + currentStart });
          inDeleted = false;
        }
        if (!inInserted) {
          inInserted = true;
          currentStart = i;
        }
      } else if (charDeleted) {
        if (inInserted) {
          edits.push({ type: 'inserted', text: text.substring(currentStart, i), element: textObj, startOffset: currentStart, endOffset: i - 1, position: elementStartIdx + currentStart, startIndex: elementStartIdx + currentStart });
          inInserted = false;
        }
        if (!inDeleted) {
          inDeleted = true;
          currentStart = i;
        }
      } else {
        if (inInserted) {
          edits.push({ type: 'inserted', text: text.substring(currentStart, i), element: textObj, startOffset: currentStart, endOffset: i - 1, position: elementStartIdx + currentStart, startIndex: elementStartIdx + currentStart });
          inInserted = false;
        }
        if (inDeleted) {
          edits.push({ type: 'deleted', text: text.substring(currentStart, i), element: textObj, startOffset: currentStart, endOffset: i - 1, position: elementStartIdx + currentStart, startIndex: elementStartIdx + currentStart });
          inDeleted = false;
        }
      }
    }

    if (inInserted) {
      edits.push({ type: 'inserted', text: text.substring(currentStart), element: textObj, startOffset: currentStart, endOffset: text.length - 1, position: elementStartIdx + currentStart, startIndex: elementStartIdx + currentStart });
    }
    if (inDeleted) {
      edits.push({ type: 'deleted', text: text.substring(currentStart), element: textObj, startOffset: currentStart, endOffset: text.length - 1, position: elementStartIdx + currentStart, startIndex: elementStartIdx + currentStart });
    }

    state.currentIdx += text.length;
  } else if (element.getNumChildren) {
    for (var j = 0; j < element.getNumChildren(); j++) {
      findEditsInElement(element.getChild(j), edits, state);
    }
  }
}

function resolveEdit(idx, action) {
  var edits = getEditsList();
  if (idx >= edits.length) return;
  var edit = edits[idx];

  // מטפלים ב-insertPart קודם (הוא בדרך כלל אחרי ה-deletePart), ואז ב-deletePart —
  // כדי שהאינדקסים בתוך אותו element לא יזוזו.

  if (edit.insertPart) {
    var p = edit.insertPart;
    var textObj = p.element.asText();
    if (action === 'accept') {
      // השאר, אבל נקה עיצוב
      textObj.setUnderline(p.startOffset, p.endOffset, false);
      textObj.setForegroundColor(p.startOffset, p.endOffset, null);
    } else {
      // דחה: מחק את הטקסט שהוכנס
      textObj.deleteText(p.startOffset, p.endOffset);
    }
  }

  if (edit.deletePart) {
    var p = edit.deletePart;
    var textObj = p.element.asText();
    if (action === 'accept') {
      // אשר: מחק את הטקסט המקורי
      textObj.deleteText(p.startOffset, p.endOffset);
    } else {
      // דחה: החזר את עיצוב המקור
      textObj.setStrikethrough(p.startOffset, p.endOffset, false);
      textObj.setForegroundColor(p.startOffset, p.endOffset, null);
    }
  }
}
