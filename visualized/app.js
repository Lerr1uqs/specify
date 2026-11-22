/* 浏览器只读取同目录的示例快照；所有交互都在本地执行。 */
"use strict";

/**
 * @typedef {{idx: number, action: string, date: string, changeId: string | null, source: string, title: string, content: string}} Version
 * @typedef {{id: string, title: string, kind: string, status: string, path: string}} Change
 * @typedef {{ref: string, status: string, records: Version[]}} ContractHistory
 * @typedef {{contracts: Record<string, ContractHistory>, changes: Record<string, Change>}} ExampleSnapshot
 */

class ProjectAtlas {
  /**
   * 读取快照，绑定图谱和时间线，再展示默认 Contract 的最新版。
   * @param {ExampleSnapshot} snapshot
   */
  constructor(snapshot) {
    this.snapshot = snapshot;
    this.contractButtons = document.querySelectorAll("[data-contract]");
    this.nodeButtons = document.querySelectorAll("[data-node]");
    this.versionList = document.getElementById("version-list");
    this.diagram = document.querySelector(".diagram");
    this.versionButtons = new Map();
    this.inspectedNode = "contract";

    for (const button of this.nodeButtons) {
      button.addEventListener("click", () => this.selectNode(button.dataset.node));
    }
    for (const button of this.contractButtons) {
      button.addEventListener("click", () => this.selectContract(button.dataset.contract));
    }
    this.selectContract("expiry");
  }

  /**
   * 选中一种完整引用，以倒序显示该 Contract 的版本。
   * @param {string} key
   */
  selectContract(key) {
    this.history = this.snapshot.contracts[key];
    this.inspectedNode = "contract";
    for (const button of this.contractButtons) {
      button.setAttribute("aria-pressed", String(button.dataset.contract === key));
    }
    this.versionList.replaceChildren();
    this.versionButtons.clear();
    const ordered = [...this.history.records].reverse();
    for (const record of ordered) {
      this.addVersionButton(record);
    }
    this.selectVersion(ordered[0]);
  }

  /**
   * 生成一个时间线按钮；选择旧版本时保留键盘焦点。
   * @param {Version} record
   */
  addVersionButton(record) {
    const change = this.snapshot.changes[record.changeId];
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    const dot = document.createElement("span");
    dot.className = "timeline-dot";
    dot.setAttribute("aria-hidden", "true");
    const label = document.createElement("span");
    const heading = document.createElement("span");
    heading.className = "timeline-label";
    heading.textContent = `#${record.idx} ${this.actionLabel(record)}`;
    const origin = document.createElement("span");
    origin.className = "timeline-origin";
    origin.textContent = change?.title || "已有正文的初始快照";
    label.append(heading, origin);
    button.append(dot, label);
    button.addEventListener("click", () => this.selectVersion(record));
    item.append(button);
    this.versionList.append(item);
    this.versionButtons.set(record.idx, button);
  }

  /**
   * 版本详情、关系图和变更来源一起更新。
   * @param {Version} record
   */
  selectVersion(record) {
    this.version = record;
    this.change = this.snapshot.changes[record.changeId];
    for (const [index, button] of this.versionButtons) {
      button.setAttribute("aria-pressed", String(index === record.idx));
    }

    const latest = this.history.records.at(-1).idx === record.idx;
    this.write("version-state", latest ? "当前版本" : `历史版本 #${record.idx}`);
    this.write("version-title", record.title || "已删除");
    this.write("version-content", record.content || "该 Contract 在这个版本被删除。");
    this.write("version-date", record.date);
    document.getElementById("version-date").dateTime = record.date.replace(" ", "T");

    // 初始回填只指向快照；同步版本可直接打开真实归档。
    const link = document.getElementById("change-link");
    if (this.change) {
      this.write("change-state", "来源 change · 已归档");
      this.write("change-title", this.change.title);
      link.href = `../example_specs/${this.change.path}/change.md`;
      link.hidden = false;
    } else {
      this.write("change-state", "来源");
      this.write("change-title", "已有正文的初始回填");
      link.hidden = true;
    }
    const previous = this.history.records[this.history.records.indexOf(record) - 1];
    this.renderComparison(previous, record);
    this.renderDiagram();
  }

  /**
   * 把相邻快照并排展示，保留各版本的完整标题和正文。
   * @param {Version | undefined} previous
   * @param {Version} current
   */
  renderComparison(previous, current) {
    const details = document.getElementById("comparison");
    details.hidden = !previous;
    if (!previous) {
      details.open = false;
      return;
    }
    this.write("before-label", `#${previous.idx} 变更前`);
    this.write("before-title", previous.title || "已删除");
    this.write("before-content", previous.content);
    this.write("after-label", `#${current.idx} 变更后`);
    this.write("after-title", current.title || "已删除");
    this.write("after-content", current.content);
  }

  /** 更新图上的身份、目标路径和对应的同步边。 */
  renderDiagram() {
    const [type, spec, id] = this.history.ref.split(":");
    this.diagram.dataset.linked = String(Boolean(this.change));
    this.write("map-type", type);
    this.write("map-spec", spec);
    this.write("map-contract", id);
    this.write("map-change", this.change?.id || "初始回填");
    this.write("map-delta", this.change ? `${type}/${spec}.md` : "无同步 delta");
    this.selectNode(this.inspectedNode);
  }

  /**
   * 解释选中节点，显示当前示例对应的身份或实际路径。
   * @param {string} key
   */
  selectNode(key) {
    const [type, spec] = this.history.ref.split(":");
    const delta = `${type}/${spec}.md`;
    const nodes = {
      type: ["type", "在项目配置里定义的正式规范类别。一个 type 可以有多份 spec。", `spec/config.yaml · specTypes.${type}`],
      spec: ["spec", "一份当前生效的规范文档。用 type 和 spec ID 定位，正文由多条 Contract 组成。", `spec/specs/${type}/${spec}/spec.md`],
      contract: ["Contract", "正式 spec 里按 ID 定位的规范条目。一个 ID 在所属 spec 内唯一。", this.history.ref],
      kind: ["kind", "在项目配置里定义的变更类别。一个 change 属于一个 kind，可同时影响多种 type 的 spec。", "spec/config.yaml · kinds.feat"],
      change: ["change", this.change ? "一次变更的材料集合。change ID 在整个项目中唯一，目录状态由工作流决定。" : "初始回填保存已有正文，此版本没有关联的 change。", this.change?.path || "source: backfill"],
      delta: ["delta", this.change ? "一份 delta 对应本 change 的一个目标 spec，可用显式 ID 更新多条 Contract。" : "此版本来自初始回填，没有产生同步 delta。", this.change ? `${this.change.path}/deltas/${delta}` : "source: backfill"],
    };
    this.inspectedNode = key;
    for (const button of this.nodeButtons) {
      button.setAttribute("aria-pressed", String(button.dataset.node === key));
    }
    const [title, description, path] = nodes[key];
    this.write("inspector-title", title);
    this.write("inspector-description", description);
    this.write("inspector-path", path);
  }

  /**
   * 使用可读动词区分已有正文回填和成功同步的变更。
   * @param {Version} record
   * @returns {string}
   */
  actionLabel(record) {
    if (record.source === "backfill") return "初始回填";
    return {add: "新增", modify: "修改", remove: "删除"}[record.action];
  }

  /**
   * 以文本节点展示仓库内容，避免 Markdown 或路径被解释为 HTML。
   * @param {string} id
   * @param {string} value
   */
  write(id, value) {
    document.getElementById(id).textContent = value;
  }
}

new ProjectAtlas(exampleSnapshot);
