# Human Audit Notebook

This is a small browser notebook for line-by-line human checking of the
Jeffrey-Kirwan implementation.

Readers can use it in either of two ways.

Online, use the GitHub Pages version:

```text
https://szqzs.github.io/Pairing-matrix-r5-d1-h22/audit_notebook/
```

Locally, after cloning or downloading the repository, open:

```text
audit_notebook/index.html
```

GitHub's ordinary file viewer shows HTML source code instead of running the
notebook, so use the Pages link or open the downloaded HTML file in a browser.

The notebook saves progress in your browser's local storage.  Use the export
buttons regularly to save a JSON backup or a Markdown audit log.
Nothing is sent anywhere; the notebook is a static local HTML file.

The checklist is organized from mathematical meaning to source code:

1. repository claims and reading path;
2. JK formula notation and specialization;
3. paper-faithful symbolic source code;
4. fast modular evaluator;
5. basis, certificates, and c12 relation artifacts.

The goal is not to read Python like a programmer.  The goal is to be able to
write, for each line of the implementation map, a short mathematical sentence:
"this code computes this factor in the JK formula, with these inputs, and this
check tells me it agrees with the slower formula layer."
