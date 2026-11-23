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
if (impactTree) new ImpactCurves(impactTree);

/** 用原生弹窗展示当前正文，支持键盘打开和 Escape 关闭。 */
document.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-current-contract]");
  if (trigger) {
    document.getElementById(trigger.getAttribute("aria-controls")).showModal();
  } else if (event.target.closest("[data-close-contract]")) {
    event.target.closest("dialog").close();
  }
});

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
