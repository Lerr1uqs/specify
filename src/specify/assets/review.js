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
