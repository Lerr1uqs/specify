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

class DiagramRenderer {
  /**
   * 把服务端生成的 Pele 容器挂载成 SVG，源码保留在 details 中可复制。
   * @param {HTMLElement} figure
   */
  constructor(figure) {
    this.figure = figure;
    this.canvas = figure.querySelector("[data-pele-canvas]");
    this.source = figure.querySelector(".diagram-source code");
  }

  /** 渲染失败时保留可读源码，不让空画布挡住正文。 */
  render() {
    if (!this.canvas || !this.source) return;
    if (!window.pele || typeof window.pele.mount !== "function") {
      this.canvas.textContent = "图表渲染器未加载，请展开下方源码。";
      return;
    }
    try {
      window.pele.mount(this.canvas, this.source.textContent);
      this.figure.classList.add("is-rendered");
    } catch {
      this.canvas.textContent = "图表渲染失败，请展开下方源码检查语法。";
    }
  }
}

for (const figure of document.querySelectorAll("[data-pele]")) {
  new DiagramRenderer(figure).render();
}

class FindBar {
  /**
   * 管理查找栏：快捷键、条件切换、正文命中步进和计数同步。
   * @param {HTMLFormElement} form
   */
  constructor(form) {
    this.form = form;
    this.input = form.querySelector('input[type="search"]');
    this.initial = form.dataset.query || "";
    this.counter = form.querySelector("[data-find-count]");
    // 图表源码默认折叠，不参与步进，和计数口径保持一致。
    this.marks = [...document.querySelectorAll("main mark")]
      .filter((mark) => !mark.closest(".diagram-source"));
    this.index = 0;
    document.addEventListener("keydown", (event) => this.onKeydown(event));
    form.addEventListener("keydown", (event) => this.onFieldKeydown(event));
    // 隐式提交由 Enter 的默认行为触发，keypress 也一并拦下更稳妥。
    form.addEventListener("keypress", (event) => this.onFieldKeypress(event));
    form.querySelector("[data-find-prev]")
      ?.addEventListener("click", () => this.step(-1));
    form.querySelector("[data-find-next]")
      ?.addEventListener("click", () => this.step(1));
    // 条件变化立即重新搜索，和常见查找栏一致。
    for (const control of form.querySelectorAll(
      '.find-toggle input, select[name="type"]',
    )) {
      control.addEventListener("change", () => this.research());
    }
    if (this.counter && this.marks.length) this.update();
    this.revealFirstMatch();
  }

  /** 只在没有修饰键、焦点不在编辑控件或弹窗内时响应 /。 */
  isShortcut(event) {
    if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return false;
    if (document.querySelector("dialog[open]")) return false;
    const target = event.target;
    return !(target instanceof HTMLElement && (
      target.isContentEditable
      || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
    ));
  }

  /** / 聚焦查找框；Escape 先清空输入，再退出搜索结果。 */
  onKeydown(event) {
    if (this.isShortcut(event)) {
      event.preventDefault();
      this.input.focus();
      this.input.select();
      return;
    }
    if (event.key !== "Escape" || document.activeElement !== this.input) return;
    event.preventDefault();
    if (this.input.value) {
      this.input.value = "";
    } else if (this.form.dataset.clearUrl) {
      location.href = this.form.dataset.clearUrl;
    }
  }

  /** 查询未变时 Enter 跳下一个命中、Shift+Enter 返回上一个。 */
  onFieldKeydown(event) {
    if (event.key !== "Enter") return;
    if (!this.marks.length || this.input.value.trim() !== this.initial) return;
    event.preventDefault();
    this.step(event.shiftKey ? -1 : 1);
  }

  /** 已经切换命中时，阻止 keypress 触发表单提交。 */
  onFieldKeypress(event) {
    if (event.key !== "Enter") return;
    if (!this.marks.length || this.input.value.trim() !== this.initial) return;
    event.preventDefault();
  }

  /** 输入或条件变化后提交新查询；空查询时保持当前页面。 */
  research() {
    if (!this.input.value.trim() && !this.initial) return;
    this.form.requestSubmit();
  }

  /** 循环移动到上/下一处高亮，并让页面跟随当前命中。 */
  step(delta) {
    if (!this.marks.length) return;
    this.index = (this.index + delta + this.marks.length) % this.marks.length;
    this.update();
    this.marks[this.index].scrollIntoView({block: "center"});
  }

  /** 标记当前命中并同步计数文本。 */
  update() {
    for (const mark of this.marks) mark.classList.remove("is-current-hit");
    this.marks[this.index].classList.add("is-current-hit");
    if (this.counter) {
      this.counter.textContent = `${this.index + 1}/${this.marks.length}`;
    }
  }

  /** 搜索视图才自动定位；带锚点和已在视野内时不打扰阅读位置。 */
  revealFirstMatch() {
    if (!this.initial || location.hash || !this.marks.length) return;
    const rect = this.marks[0].getBoundingClientRect();
    if (rect.top < 0 || rect.top > innerHeight * 0.7) {
      this.marks[0].scrollIntoView({block: "center"});
    }
  }
}

const searchForm = document.querySelector("[data-spec-search]");
if (searchForm) new FindBar(searchForm);

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

/** 预览正式 Contract 的标题和摘要，点击引用仍按链接跳转。 */
class ContractReferencePreview {
  constructor() {
    this.element = document.createElement("aside");
    this.element.id = "contract-reference-preview";
    this.element.className = "contract-reference-preview";
    this.element.setAttribute("role", "tooltip");
    this.element.hidden = true;
    this.title = document.createElement("strong");
    this.body = document.createElement("p");
    this.element.append(this.title, this.body);
    document.body.append(this.element);

    document.addEventListener("pointerover", (event) => {
      const link = event.target.closest("[data-reference-title]");
      if (link && event.pointerType !== "touch") this.open(link);
    });
    document.addEventListener("pointerout", (event) => {
      if (this.link?.contains(event.target) && !this.link.contains(event.relatedTarget)
        && !this.link.matches(":focus-visible")) this.close();
    });
    document.addEventListener("focusin", (event) => {
      const link = event.target.closest("[data-reference-title]");
      if (link) this.open(link);
    });
    document.addEventListener("focusout", (event) => {
      if (event.target === this.link) this.close();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && this.link) {
        event.stopImmediatePropagation();
        this.close();
      }
    });
    window.addEventListener("scroll", () => this.close(), true);
    window.addEventListener("resize", () => this.close());
  }

  /** 将提示框锚定在引用旁，长摘要也保持在视口内。
   * @param {HTMLAnchorElement} link
   */
  open(link) {
    if (this.link === link) return;
    this.close();
    this.link = link;
    this.title.textContent = link.dataset.referenceTitle;
    this.body.textContent = link.dataset.referencePreview;
    link.setAttribute("aria-describedby", this.element.id);
    this.element.hidden = false;
    const anchor = link.getBoundingClientRect();
    const {width, height} = this.element.getBoundingClientRect();
    const left = Math.max(8, Math.min(anchor.left, innerWidth - width - 8));
    const top = anchor.bottom + height + 8 > innerHeight
      ? Math.max(8, anchor.top - height - 8)
      : anchor.bottom + 8;
    this.element.style.left = `${left}px`;
    this.element.style.top = `${top}px`;
  }

  /** 清除提示和关联，避免正文切换后保留旧内容。 */
  close() {
    this.link?.removeAttribute("aria-describedby");
    this.link = null;
    this.element.hidden = true;
  }
}

new ContractReferencePreview();

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
