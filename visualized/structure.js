/* 当前仓库的三份 spec 与明确标注的演示分支共用同一棵树。 */
"use strict";

const structureTypes = [
  {id: "capability", label: "可观察的能力", specs: [
    {id: "account-recovery", contracts: ["request-recovery", "reset-password"]},
    {id: "user-auth", contracts: ["password-login", "passkey-login", "session-expiry"]},
  ]},
  {id: "component", label: "模块职责", specs: [
    {id: "auth-service", contracts: ["credential-validation", "session-issuance"]},
    {id: "notification-service", demo: true, contracts: ["delivery", "retry-policy"]},
  ]},
  {id: "requirement", label: "业务目标", specs: [
    {id: "account-safety", demo: true, contracts: ["recover-access", "verify-identity"]},
    {id: "service-reliability", demo: true, contracts: ["delivery-target", "failure-reporting"]},
  ]},
  {id: "architecture", label: "系统结构", specs: [
    {id: "identity-platform", demo: true, contracts: ["service-boundaries", "data-flow"]},
    {id: "event-delivery", demo: true, contracts: ["event-routing", "dependency-direction"]},
  ]},
  {id: "rule", label: "跨规范约束", specs: [
    {id: "recovery-policy", demo: true, contracts: ["challenge-expiry", "attempt-limits"]},
    {id: "audit-policy", demo: true, contracts: ["event-fields", "retention"]},
  ]},
];

const structureActions = {
  add: {label: "新增", color: "#147548"},
  modify: {label: "修改", color: "#2855bc"},
  rename: {label: "改名", color: "#7836a9"},
  remove: {label: "删除", color: "#a52a50"},
};

const structureChanges = [
  {id: "add-passkey-login", label: "增加通行密钥登录", source: "真实", targets: {
    "capability:user-auth": {"password-login": ["modify"], "passkey-login": ["add"]},
    "component:auth-service": {"credential-validation": ["modify"]},
  }},
  {id: "expire-idle-sessions", label: "增加会话空闲超时", source: "真实", targets: {
    "capability:user-auth": {"session-expiry": ["modify"]},
    "component:auth-service": {"session-issuance": ["rename", "modify"]},
  }},
  {id: "publish-recovery-controls", label: "调整账号恢复约束", source: "演示", targets: {
    "capability:account-recovery": {"request-recovery": ["modify"]},
    "requirement:account-safety": {"verify-identity": ["modify"]},
    "architecture:identity-platform": {"data-flow": ["modify"]},
    "rule:recovery-policy": {"challenge-expiry": ["modify"], "attempt-limits": ["remove"]},
  }},
];

/**
 * 创建树节点的普通 HTML 元素，用文本节点写入内容。
 * @param {string} tag
 * @param {string} [className]
 * @param {string} [text]
 * @returns {HTMLElement}
 */
function structureElement(tag, className = "", text = "") {
  const element = document.createElement(tag);
  element.className = className;
  element.textContent = text;
  return element;
}

/**
 * 沿指定的折线路径绘制圆角，短线段会自动缩小圆角半径。
 * @param {Array<[number, number]>} points
 * @returns {Path2D}
 */
function roundedStructurePath(points) {
  const path = new Path2D();
  path.moveTo(...points[0]);
  for (let index = 1; index < points.length - 1; index += 1) {
    const [x, y] = points[index];
    const [previousX, previousY] = points[index - 1];
    const [nextX, nextY] = points[index + 1];
    const radius = Math.min(9, Math.hypot(x - previousX, y - previousY) / 2, Math.hypot(x - nextX, y - nextY) / 2);
    path.arcTo(x, y, nextX, nextY, radius);
  }
  path.lineTo(...points.at(-1));
  return path;
}

class SpecStructure {
  /** 初始化目录树、并排展示的变更以及独立的连线绘图层。 */
  constructor() {
    this.board = document.getElementById("structure-board");
    this.canvas = document.getElementById("structure-connections");
    this.context = this.canvas.getContext("2d");
    this.tree = document.getElementById("structure-targets");
    this.sources = document.getElementById("structure-sources");
    this.result = document.getElementById("structure-result");
    this.specs = new Map();
    this.changes = new Map();
    this.frame = null;
    this.motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    this.stacked = window.matchMedia("(max-width: 49rem)");

    this.renderTree(document.getElementById("structure-types"));
    this.renderChanges();
    this.board.addEventListener("toggle", () => this.scheduleDraw(), true);
    new ResizeObserver(() => this.scheduleDraw()).observe(this.board);
    this.selectChange(structureChanges[0].id);
  }

  /** 平铺每个 change 的 delta，并记录各类操作在卡片中的起点。 */
  renderChanges() {
    const legend = document.getElementById("structure-legend");
    for (const key of Object.keys(structureActions)) {
      const entry = document.createElement("li");
      entry.append(this.badge(key));
      legend.append(entry);
    }
    const cards = document.getElementById("structure-changes");
    for (const change of structureChanges) {
      const card = structureElement("article", "structure-change");
      const button = structureElement("button", "structure-change-title");
      button.type = "button";
      button.setAttribute("aria-pressed", "false");
      button.append(structureElement("strong", "", change.label), structureElement("code", "", change.id), structureElement("span", "structure-demo", change.source));
      button.addEventListener("click", () => this.selectChange(change.id));
      const deltas = structureElement("ul", "structure-deltas");
      const edges = [];
      for (const [ref, operations] of Object.entries(change.targets)) {
        const delta = structureElement("li", "structure-delta");
        delta.append(structureElement("code", "structure-delta-path", `deltas/${ref.replace(":", "/")}.md`));
        const rows = structureElement("ul", "structure-delta-actions");
        const wiredActions = new Set();
        for (const [id, keys] of Object.entries(operations)) {
          for (const key of keys) {
            const row = document.createElement("li");
            row.append(this.badge(key), structureElement("code", "", id));
            rows.append(row);
            // 同一份 delta 的同类动作共用一条线，明细仍逐项列出。
            if (!wiredActions.has(key)) {
              edges.push({ref, key, row});
              wiredActions.add(key);
            }
          }
        }
        delta.append(rows);
        deltas.append(delta);
      }
      card.append(button, deltas);
      cards.append(card);
      this.changes.set(change.id, {change, card, button, edges});
    }
  }

  /**
   * 显示 action 的颜色和名称，颜色之外仍可读出含义。
   * @param {string} key
   */
  badge(key) {
    const badge = structureElement("span", `structure-operation action-${key}`, structureActions[key].label);
    return badge;
  }

  /**
   * type 和 spec 均使用原生详情控件，支持键盘展开。
   * @param {HTMLElement} tree
   */
  renderTree(tree) {
    for (const type of structureTypes) {
      const li = structureElement("li", "structure-type");
      const detail = document.createElement("details");
      detail.open = true;
      const title = structureElement("summary", "structure-type-label");
      title.append(structureElement("code", "", type.id), structureElement("span", "", type.label));
      const specs = structureElement("ul", "structure-specs");
      for (const [index, spec] of type.specs.entries()) {
        const item = document.createElement("li");
        const file = document.createElement("details");
        // 每个 type 首屏都露出至少一份 spec 的 Contract ID。
        file.open = !spec.demo || index === 0;
        const heading = structureElement("summary", "structure-spec-label");
        heading.append(structureElement("code", "", spec.id));
        if (spec.demo) heading.append(structureElement("span", "structure-demo", "演示"));
        const list = structureElement("ul", "structure-contracts");
        const contracts = new Map();
        for (const id of spec.contracts) {
          const row = structureElement("li", "structure-contract");
          const action = structureElement("span", "structure-operation-list");
          row.title = `${type.id}:${spec.id}:${id}`;
          row.append(structureElement("code", "", id), action);
          list.append(row);
          contracts.set(id, {row, action});
        }
        file.append(heading, list);
        item.append(file);
        specs.append(item);
        this.specs.set(`${type.id}:${spec.id}`, {detail, file, heading, contracts});
      }
      detail.append(title, specs);
      li.append(detail);
      tree.append(li);
    }
  }

  /**
   * 展开这个 change 命中的分支，在 Contract 节点展示对应 action。
   * @param {string} id
   */
  selectChange(id) {
    this.selected = this.changes.get(id);
    const {change} = this.selected;
    for (const entry of this.changes.values()) {
      entry.button.setAttribute("aria-pressed", String(entry === this.selected));
    }
    let count = 0;
    for (const [ref, spec] of this.specs) {
      const operations = change.targets[ref];
      spec.heading.classList.toggle("is-affected", Boolean(operations));
      if (operations) {
        spec.detail.open = true;
        spec.file.open = true;
      }
      for (const [id, {row, action}] of spec.contracts) {
        const keys = operations?.[id] || [];
        row.classList.toggle("is-affected", keys.length > 0);
        action.replaceChildren(...keys.map(key => this.badge(key)));
        if (keys.length) count += 1;
      }
    }
    this.result.textContent = `${change.label}影响 ${Object.keys(change.targets).length} 份 spec、${count} 条 Contract。`;
    this.startedAt = performance.now();
    this.scheduleDraw();
  }

  /** 合并同一帧内的选择、展开和尺寸变化，使用更新后的布局坐标。 */
  scheduleDraw() {
    if (this.frame !== null) return;
    this.frame = requestAnimationFrame(time => {
      this.frame = null;
      this.draw(time);
    });
  }

  /**
   * 将每条 action 线分配给独立轨道，并用圆弧转弯接入 spec。
   * @param {number} time
   */
  draw(time) {
    const board = this.board.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    const width = Math.round(board.width * ratio);
    const height = Math.round(board.height * ratio);
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    const context = this.context;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, board.width, board.height);

    const tree = this.tree.getBoundingClientRect();
    const sources = this.sources.getBoundingClientRect();
    const card = this.selected.card.getBoundingClientRect();
    const elapsed = time - this.startedAt;
    const moving = !this.motion.matches && elapsed < 1100;
    const edges = this.selected.edges.filter(edge => this.specs.get(edge.ref).heading.getClientRects().length);
    const stacked = this.stacked.matches;
    const treeBottom = tree.bottom - board.top;
    const routeHeight = sources.top - tree.bottom;
    for (const [index, {ref, key, row}] of edges.entries()) {
      const heading = this.specs.get(ref).heading;
      const target = heading.getBoundingClientRect();
      const operation = row.getBoundingClientRect();
      const siblings = edges.filter(edge => edge.ref === ref);
      const port = siblings.findIndex(edge => edge.key === key) + 1;
      const startX = (stacked ? card.right : card.left + card.width * (index + 1) / (edges.length + 1)) - board.left;
      const startY = (stacked ? operation.top + operation.height / 2 : card.top) - board.top;
      const x = (stacked ? target.right + 1 : target.left - 1) - board.left;
      const y = target.top + target.height * port / (siblings.length + 1) - board.top;
      const direction = stacked ? -1 : 1;
      // 大屏在线树下的空带内分轨，窄屏把线路挪到卡片右侧。
      const trackX = stacked ? tree.right - board.left + 6 + index * 7 : x - 7 - (edges.length - 1 - index) * 2.5;
      const trackY = treeBottom + routeHeight * (edges.length - index) / (edges.length + 1);
      const points = [[startX, startY]];
      if (!stacked) points.push([startX, trackY], [trackX, trackY]);
      else points.push([trackX, startY]);
      points.push([trackX, y], [x - direction * 4, y]);
      const color = structureActions[key].color;
      const path = roundedStructurePath(points);

      context.lineWidth = 2;
      context.lineCap = "round";
      context.strokeStyle = color;
      context.stroke(path);
      if (moving) {
        context.setLineDash([7, 20]);
        context.lineDashOffset = -elapsed / 14;
        context.strokeStyle = "#ffffffb3";
        context.lineWidth = 1;
        context.stroke(path);
        context.setLineDash([]);
      }
      context.fillStyle = color;
      context.beginPath();
      context.arc(startX + (stacked ? 2 : 0), startY - (stacked ? 0 : 2), 3, 0, Math.PI * 2);
      context.fill();
      context.beginPath();
      context.moveTo(x, y);
      context.lineTo(x - direction * 7, y - 3.5);
      context.lineTo(x - direction * 7, y + 3.5);
      context.closePath();
      context.fill();
    }
    if (moving && edges.length) this.scheduleDraw();
  }
}

new SpecStructure();
