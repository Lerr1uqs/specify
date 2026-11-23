/* 按页面实际位置绘制 Change 到各 Spec 的曲线，Contract 折线仍由 CSS 排版。 */
"use strict";

class ImpactCurves {
  /**
   * 页面重排后刷新连线；展开 diff 时下方的 Spec 会移动。
   * @param {HTMLElement} tree
   */
  constructor(tree) {
    this.tree = tree;
    this.svg = tree.querySelector(".impact-curves");
    this.source = tree.querySelector(".impact-source");
    this.targets = [...tree.querySelectorAll(".impact-branches > li")].map(
      (branch) => branch.querySelector(".target-node") || branch.firstElementChild,
    );
    const observer = new ResizeObserver(() => this.draw());
    observer.observe(tree);
    tree.addEventListener("toggle", () => this.draw(), true);
  }

  /** 用水平切线连到节点左右边的中心，不让线段拼接或穿过卡片。 */
  draw() {
    if (this.tree.classList.contains("is-inspecting")) return;
    const origin = this.svg.getBoundingClientRect();
    const source = this.source.getBoundingClientRect();
    const startX = source.right - origin.left;
    const startY = source.top + source.height / 2 - origin.top;
    const curves = this.targets.map((target) => {
      const box = target.getBoundingClientRect();
      const endX = box.left - origin.left;
      const endY = box.top + box.height / 2 - origin.top;
      const midX = (startX + endX) / 2;
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute(
        "d",
        `M ${startX} ${startY} C ${midX} ${startY} ${midX} ${endY} ${endX} ${endY}`,
      );
      return path;
    });
    this.svg.replaceChildren(...curves);
  }
}

const impactTree = document.querySelector(".impact-tree");
if (impactTree) {
  new ImpactCurves(impactTree);
  const button = impactTree.closest(".change-impact").querySelector("[data-toggle-diffs]");
  const operations = [...impactTree.querySelectorAll("details.operation")];
  if (operations.length) {
    /** 单独展开或收起时，也同步更新批量操作的文字。 */
    const updateButton = () => {
      button.textContent = operations.every((item) => item.open) ? "收起全部" : "展开全部";
    };
    button.hidden = false;
    button.addEventListener("click", () => {
      const open = operations.some((item) => !item.open);
      for (const operation of operations) operation.open = open;
      updateButton();
    });
    impactTree.addEventListener("toggle", updateButton, true);
    updateButton();
  }
}

const priorityFilter = document.querySelector("[data-priority-filter]");
if (priorityFilter) {
  const trigger = priorityFilter.querySelector("summary");
  const options = [...priorityFilter.querySelectorAll(".priority-options a")];

  // 和常见筛选菜单一致，点外部收起。键盘关闭后返回触发按钮。
  document.addEventListener("click", (event) => {
    if (priorityFilter.open && !priorityFilter.contains(event.target)) {
      priorityFilter.open = false;
    }
  });
  priorityFilter.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && priorityFilter.open) {
      event.preventDefault();
      priorityFilter.open = false;
      trigger.focus();
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      priorityFilter.open = true;
      const index = options.indexOf(document.activeElement);
      const next = event.key === "ArrowDown"
        ? (index + 1) % options.length
        : (index <= 0 ? options.length - 1 : index - 1);
      options[next].focus();
    }
  });
}

/** 用原生弹窗展示当前正文，支持键盘打开和 Escape 关闭。 */
document.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-current-contract]");
  if (trigger) {
    document.getElementById(trigger.getAttribute("aria-controls")).showModal();
  } else if (event.target.closest("[data-close-contract]")) {
    event.target.closest("dialog").close();
  }
});

class SpecInspector {
  /** 复用正式 Spec 详情，同时保留原来的 Change DOM 和阅读位置。
   * @param {HTMLElement} panel
   */
  constructor(panel) {
    this.panel = panel;
    this.tree = panel.closest(".impact-tree");
    this.closeButton = panel.querySelector("[data-close-spec]");
    this.content = panel.querySelector("[data-spec-content]");
    this.closeButton.addEventListener("click", () => this.close());
    document.addEventListener("keydown", (event) => {
      if (!this.panel.hidden && event.key === "Escape") this.close();
    });
    this.tree.addEventListener("click", (event) => {
      const link = event.target.closest("[data-open-spec]");
      // 保留浏览器的新标签页操作。
      if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      if (!this.panel.hidden && this.trigger === link) this.close();
      else this.open(link);
    });
  }

  /** 收起根节点，用左右两栏同时审阅修改列表和当前 Spec。
   * @param {HTMLAnchorElement} link
   */
  async open(link) {
    if (this.panel.hidden) {
      this.returnFocus = link;
      this.position = {left: window.scrollX, top: window.scrollY};
    } else {
      this.trigger.setAttribute("aria-expanded", "false");
      this.request.abort();
    }
    this.trigger = link;
    link.setAttribute("aria-expanded", "true");
    this.content.textContent = "正在读取 Spec…";
    this.tree.classList.add("is-inspecting");
    this.panel.hidden = false;
    this.panel.scrollTop = 0;
    this.closeButton.focus({preventScroll: true});
    const bounds = this.panel.getBoundingClientRect();
    if (bounds.top < 0 || bounds.top >= innerHeight) {
      this.panel.scrollIntoView({block: "nearest"});
    }

    const request = new AbortController();
    this.request = request;
    try {
      const response = await fetch(link.href, {signal: request.signal});
      if (!response.ok) throw new Error("Spec 请求失败");
      const page = new DOMParser().parseFromString(await response.text(), "text/html");
      const detail = page.querySelector("#review");
      if (!detail) throw new Error("缺少 Spec 正文");
      if (!request.signal.aborted) this.content.replaceChildren(...detail.childNodes);
    } catch {
      if (request.signal.aborted) return;
      const fallback = document.createElement("a");
      fallback.href = link.href;
      fallback.textContent = "打开正式 Spec 页面";
      this.content.replaceChildren("暂时无法读取 Spec。", fallback);
    }
  }

  /** 还原影响树的根节点、连线和打开面板前的位置。 */
  close() {
    this.request.abort();
    this.panel.hidden = true;
    this.tree.classList.remove("is-inspecting");
    this.trigger.setAttribute("aria-expanded", "false");
    this.returnFocus.focus({preventScroll: true});
    window.scrollTo(this.position);
  }
}

const specPanel = document.querySelector("#current-spec-panel");
if (specPanel) new SpecInspector(specPanel);

class ReviewRefresh {
  /** @param {string} revision 初次生成页面时的项目版本。 */
  constructor(revision) {
    this.revision = revision;
    this.stateKey = `specify-review:${location.search}`;
    const saved = sessionStorage.getItem(this.stateKey);
    if (saved) {
      // 恢复同一页面的展开项和阅读位置，再让连线按新布局重绘。
      sessionStorage.removeItem(this.stateKey);
      const { opened, x, y } = JSON.parse(saved);
      for (const detail of document.querySelectorAll("[data-review-details]")) {
        detail.open = opened.includes(detail.dataset.reviewDetails);
      }
      requestAnimationFrame(() => window.scrollTo(x, y));
    }
    window.setTimeout(() => this.check(), 1500);
  }

  /** 有文件改动时刷新本页，避免后台页签持续请求。 */
  async check() {
    try {
      if (!document.hidden) {
        const response = await fetch("/revision");
        if (response.ok && await response.text() !== this.revision) {
          const opened = [...document.querySelectorAll("[data-review-details][open]")]
            .map((detail) => detail.dataset.reviewDetails);
          sessionStorage.setItem(this.stateKey, JSON.stringify({
            opened, x: window.scrollX, y: window.scrollY,
          }));
          location.reload();
          return;
        }
      }
    } catch {
      // 本地服务短暂不可用时保留当前页面，下轮继续探测。
    }
    window.setTimeout(() => this.check(), 1500);
  }
}

const revision = document.querySelector('meta[name="specify-revision"]').content;
if (revision) new ReviewRefresh(revision);
