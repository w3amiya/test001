const state = {
  get apiBase() {
    return document.getElementById("apiBase").value.trim().replace(/\/$/, "");
  },
};

const output = document.getElementById("output");
const serviceStatus = document.getElementById("serviceStatus");
const worksheetList = document.getElementById("worksheetList");

document.getElementById("checkService").addEventListener("click", checkService);
document.getElementById("loadWorksheets").addEventListener("click", loadWorksheets);
document.getElementById("runPlan").addEventListener("click", runImportPlan);

checkService();

async function checkService() {
  try {
    const result = await requestJson(`${state.apiBase}/health`);
    setStatus(result.ok ? "已连接" : "异常", result.ok);
    print(result);
  } catch (error) {
    setStatus("未连接", false);
    printError(error);
  }
}

async function loadWorksheets() {
  const twbPath = document.getElementById("twbPath").value.trim();
  if (!twbPath) {
    printText("请先填写 Tableau 工作簿路径。");
    return;
  }

  try {
    const url = `${state.apiBase}/worksheets?twb=${encodeURIComponent(twbPath)}`;
    const result = await requestJson(url);
    worksheetList.innerHTML = "";
    for (const name of result.worksheets || []) {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      worksheetList.appendChild(option);
    }
    print(result);
  } catch (error) {
    printError(error);
  }
}

async function runImportPlan() {
  const plan = document.getElementById("planPath").value.trim();
  if (!plan) {
    printText("请先填写导入计划 JSON 路径。");
    return;
  }

  try {
    const result = await requestJson(`${state.apiBase}/import-plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan }),
    });
    print(result);
  } catch (error) {
    printError(error);
  }
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `请求失败：${response.status}`);
  }
  return data;
}

function setStatus(text, ok) {
  serviceStatus.textContent = text;
  serviceStatus.classList.toggle("ok", ok);
  serviceStatus.classList.toggle("bad", !ok);
}

function print(data) {
  output.textContent = JSON.stringify(data, null, 2);
}

function printText(text) {
  output.textContent = text;
}

function printError(error) {
  output.textContent = `Error: ${error.message || error}`;
}
