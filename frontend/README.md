# AI Business Decision Copilot Frontend

Static SaaS web application for the AI Business Decision Copilot.

## Structure

```text
frontend/
├── index.html
├── Dockerfile
├── README.md
└── src/
    ├── scripts/
    │   ├── app.js
    │   ├── data.js
    │   ├── network-canvas.js
    │   └── router.js
    └── styles/
        └── main.css
```

## Run Locally

```powershell
cd D:\kaggle_project\capston\frontend
python -m http.server 3000
```

Open `http://localhost:3000`.

## Notes

- No Streamlit dependency.
- No build step required.
- `src/scripts/router.js` owns page navigation.
- `src/scripts/network-canvas.js` owns the animated hero background.
- `src/scripts/data.js` keeps UI copy and demo insight content separate from behavior.
