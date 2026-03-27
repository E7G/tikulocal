import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { getCurrentWindow } from "@tauri-apps/api/window";

const TYPE_MAP: Record<number, string> = {
  0: "单选题",
  1: "多选题",
  2: "填空题",
  3: "判断题",
  4: "问答题",
};

let selectedIds: Set<number> = new Set();

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initSearch();
  initImport();
  initManage();
  initDragDrop();
});

function initNavigation() {
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach((item) => {
    item.addEventListener("click", () => {
      navItems.forEach((i) => i.classList.remove("active"));
      item.classList.add("active");

      const page = (item as HTMLElement).dataset.page;
      document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
      document.getElementById(`page-${page}`)?.classList.add("active");

      if (page === "manage") {
        refreshStats();
        refreshTable();
      }
    });
  });
}

function initSearch() {
  const btnSearch = document.getElementById("btn-search");
  const input = document.getElementById("search-question") as HTMLInputElement;
  const select = document.getElementById("search-type") as HTMLSelectElement;

  btnSearch?.addEventListener("click", async () => {
    const question = input.value.trim();
    if (!question) {
      showResults("search-results", "请输入题目内容");
      return;
    }

    const type = parseInt(select.value);
    try {
      const results = await invoke<unknown[]>("search_questions", {
        question,
        qtype: type,
      });
      displaySearchResults(results);
    } catch (e) {
      showResults("search-results", `搜索失败: ${e}`);
    }
  });

  input?.addEventListener("keypress", (e) => {
    if (e.key === "Enter") btnSearch?.click();
  });
}

function displaySearchResults(results: unknown[]) {
  const container = document.getElementById("search-results");
  if (!container) return;

  if (!results.length) {
    container.innerHTML = '<div class="question-item">未找到相关题目</div>';
    return;
  }

  container.innerHTML = results
    .map((r: unknown) => {
      const item = r as Record<string, unknown>;
      const type = item.type as number;
      const options = JSON.parse(item.options as string || "[]") as string[];
      const optionsText = options
        .map((o, i) => `${String.fromCharCode(65 + i)}. ${o}`)
        .join("\n  ");

      return `
        <div class="question-item">
          <div class="question-title">【${TYPE_MAP[type] || "未知"}】答案：${item.answer}</div>
          <div class="question-content">${item.question}</div>
          ${options.length ? `<div class="question-options">选项：\n  ${optionsText}</div>` : ""}
        </div>
      `;
    })
    .join("");
}

function initImport() {
  const btnBrowse = document.getElementById("btn-browse");
  const btnImport = document.getElementById("btn-import");
  const pathInput = document.getElementById("import-path") as HTMLInputElement;
  const typeSelect = document.getElementById("import-type") as HTMLSelectElement;
  const dropZone = document.getElementById("drop-zone");

  btnBrowse?.addEventListener("click", async () => {
    const filter = typeSelect.value === "docx"
      ? [{ name: "Word", extensions: ["docx"] }]
      : [{ name: "JSON", extensions: ["json"] }];

    const selected = await open({
      multiple: true,
      filters: filter,
    });

    if (selected) {
      const files = Array.isArray(selected) ? selected : [selected];
      if (files.length === 1) {
        pathInput.value = files[0] as string;
      } else {
        pathInput.value = `${files.length} 个文件已选中`;
        await importMultipleFiles(files as string[]);
      }
    }
  });

  dropZone?.addEventListener("click", async () => {
    const filter = [
      { name: "题库文件", extensions: ["docx", "json"] },
    ];

    const selected = await open({
      multiple: true,
      filters: filter,
    });

    if (selected) {
      const files = Array.isArray(selected) ? selected : [selected];
      if (files.length === 1) {
        const file = files[0] as string;
        pathInput.value = file;
        typeSelect.value = file.endsWith(".docx") ? "docx" : "json";
        await importSingleFile(file, typeSelect.value);
      } else {
        pathInput.value = `${files.length} 个文件已选中`;
        await importMultipleFiles(files as string[]);
      }
    }
  });

  btnImport?.addEventListener("click", async () => {
    const path = pathInput.value.trim();
    if (!path || path.includes("个文件已选中")) {
      showResults("import-results", "请点击拖拽区域或浏览按钮选择文件");
      return;
    }

    await importSingleFile(path, typeSelect.value);
  });
}

function initDragDrop() {
  const dropZone = document.getElementById("drop-zone");
  if (!dropZone) return;

  getCurrentWindow().onDragDropEvent((event) => {
    if (event.payload.type === "over") {
      dropZone.classList.add("drag-over");
    } else if (event.payload.type === "drop") {
      dropZone.classList.remove("drag-over");
      const paths = event.payload.paths;
      if (paths && paths.length > 0) {
        const validFiles = paths.filter((p: string) => {
          const ext = p.split(".").pop()?.toLowerCase();
          return ext === "docx" || ext === "json";
        });

        if (validFiles.length === 0) {
          showResults("import-results", "请拖入 .docx 或 .json 文件");
          return;
        }

        importMultipleFiles(validFiles);
      }
    } else {
      dropZone.classList.remove("drag-over");
    }
  });
}

async function importSingleFile(path: string, type: string) {
  try {
    const count = type === "docx"
      ? await invoke<number>("import_docx", { path })
      : await invoke<number>("import_json", { path });

    showResults("import-results", `成功导入 ${count} 道题目`);
  } catch (e) {
    showResults("import-results", `导入失败: ${e}`);
  }
}

async function importMultipleFiles(files: string[]) {
  showResults("import-results", `正在批量导入 ${files.length} 个文件...`);

  let totalCount = 0;
  let failedCount = 0;
  const failedFiles: string[] = [];

  for (const file of files) {
    try {
      const ext = file.split(".").pop()?.toLowerCase();
      const count = ext === "docx"
        ? await invoke<number>("import_docx", { path: file })
        : await invoke<number>("import_json", { path: file });
      totalCount += count;
    } catch (e) {
      failedCount++;
      failedFiles.push(file);
    }
  }

  let result = `批量导入完成！成功导入 ${totalCount} 道题目`;
  if (failedCount > 0) {
    result += `\n\n失败文件 (${failedCount}):\n${failedFiles.join("\n")}`;
  }
  showResults("import-results", result);
}

function initManage() {
  const btnRefresh = document.getElementById("btn-refresh");
  const btnDelete = document.getElementById("btn-delete");
  const btnClear = document.getElementById("btn-clear");
  const selectAll = document.getElementById("select-all") as HTMLInputElement;

  btnRefresh?.addEventListener("click", () => {
    refreshStats();
    refreshTable();
  });

  btnDelete?.addEventListener("click", async () => {
    if (selectedIds.size === 0) {
      alert("请选择要删除的题目");
      return;
    }

    if (!confirm(`确定删除选中的 ${selectedIds.size} 道题目？`)) return;

    for (const id of selectedIds) {
      try {
        await invoke("delete_question", { id });
      } catch (e) {
        console.error(`Failed to delete ${id}:`, e);
      }
    }

    selectedIds.clear();
    refreshStats();
    refreshTable();
  });

  btnClear?.addEventListener("click", async () => {
    if (!confirm("确定清空整个题库？此操作不可恢复！")) return;

    try {
      await invoke("clear_all");
      selectedIds.clear();
      refreshStats();
      refreshTable();
    } catch (e) {
      alert(`清空失败: ${e}`);
    }
  });

  selectAll?.addEventListener("change", () => {
    const checkboxes = document.querySelectorAll("#questions-body input[type='checkbox']") as NodeListOf<HTMLInputElement>;
    checkboxes.forEach((cb) => {
      cb.checked = selectAll.checked;
      const id = parseInt(cb.dataset.id || "0");
      if (selectAll.checked) {
        selectedIds.add(id);
      } else {
        selectedIds.delete(id);
      }
    });
  });
}

async function refreshStats() {
  try {
    const stats = await invoke<Record<string, number>>("get_stats");
    const total = document.getElementById("stat-total");
    const single = document.getElementById("stat-single");
    const multi = document.getElementById("stat-multi");
    const judge = document.getElementById("stat-judge");

    if (total) total.textContent = String(stats.total || 0);
    if (single) single.textContent = String(stats.single || 0);
    if (multi) multi.textContent = String(stats.multi || 0);
    if (judge) judge.textContent = String(stats.judge || 0);
  } catch (e) {
    console.error("Failed to get stats:", e);
  }
}

async function refreshTable() {
  const tbody = document.getElementById("questions-body");
  if (!tbody) return;

  try {
    const questions = await invoke<unknown[]>("get_questions", { limit: 100 });

    tbody.innerHTML = questions
      .map((q: unknown) => {
        const item = q as Record<string, unknown>;
        const id = item.id as number;
        const question = (item.question as string || "").slice(0, 50);
        const type = item.type as number;
        const answer = (item.answer as string || "").slice(0, 20);
        const createdAt = item.created_at as string || "";

        return `
          <tr>
            <td><input type="checkbox" data-id="${id}"></td>
            <td>${id}</td>
            <td>${question}${(item.question as string || "").length > 50 ? "..." : ""}</td>
            <td>${TYPE_MAP[type] || "未知"}</td>
            <td>${answer}${(item.answer as string || "").length > 20 ? "..." : ""}</td>
            <td>${createdAt}</td>
          </tr>
        `;
      })
      .join("");

    tbody.querySelectorAll("input[type='checkbox']").forEach((cb) => {
      cb.addEventListener("change", () => {
        const id = parseInt((cb as HTMLInputElement).dataset.id || "0");
        if ((cb as HTMLInputElement).checked) {
          selectedIds.add(id);
        } else {
          selectedIds.delete(id);
        }
      });
    });
  } catch (e) {
    console.error("Failed to get questions:", e);
  }
}

function showResults(containerId: string, text: string) {
  const container = document.getElementById(containerId);
  if (container) {
    container.textContent = text;
  }
}
