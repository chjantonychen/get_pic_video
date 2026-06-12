"""Minimal test to verify Qt WebEngine JS injection works"""
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

app = QApplication(sys.argv)
win = QWidget()
win.setWindowTitle("WebEngine Test")
win.resize(800, 600)
layout = QVBoxLayout(win)

web = QWebEngineView()
web.setUrl(QUrl("https://www.baidu.com"))
layout.addWidget(web)

label = QLabel("等待测试...")
layout.addWidget(label)
info = QLabel("")
layout.addWidget(info)

def test_js():
    web.page().runJavaScript("document.title", lambda t: info.setText(f"当前标题: {t}"))
    web.page().runJavaScript("document.body.style.backgroundColor = 'lightblue';", lambda r: info.setText(info.text() + "\n背景变色: " + str(r)))
    web.page().runJavaScript("""(function(){var s=document.createElement('style');s.textContent='*:hover{outline:3px solid red!important}';document.head.appendChild(s);return document.title;})()""", lambda r: info.setText(info.text() + "\nCSS注入完成, 标题: " + str(r)))

btn = QPushButton("测试 JS 注入")
btn.clicked.connect(test_js)
layout.addWidget(btn)

win.show()
sys.exit(app.exec_())
