/** 创建 SVG 元素，所有节点名称和链接都通过 DOM 属性写入。 */
function graphElement(tag, attributes = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [name, value] of Object.entries(attributes)) {
    element.setAttribute(name, value);
  }
  return element;
}

/** 用排斥力分开节点，用弹簧力将有引用的节点拉近。 */
function layoutSpecGraph(nodes, edges) {
  // 从固定的螺旋坐标出发，同一项目刷新后仍有相同的布局。
  nodes.forEach((node, index) => {
    const angle = index * Math.PI * (3 - Math.sqrt(5));
    const radius = 86 * Math.sqrt(index);
    node.x = Math.cos(angle) * radius;
    node.y = Math.sin(angle) * radius;
  });
  // 限制大图的排斥计算量，布局只在打开页面时计算一次。
  const steps = Math.min(90, Math.floor(1600000 / nodes.length ** 2));
  for (let step = 0; step < steps; step += 1) {
    for (const node of nodes) {
      node.dx = -node.x * 0.04;
      node.dy = -node.y * 0.04;
    }
    for (const [index, node] of nodes.entries()) {
      for (let j = index + 1; j < nodes.length; j += 1) {
        const other = nodes[j];
        const x = other.x - node.x;
        const y = other.y - node.y;
        const push = 12500 / Math.max(20, Math.hypot(x, y)) ** 3;
        node.dx -= x * push;
        node.dy -= y * push;
        other.dx += x * push;
        other.dy += y * push;
      }
    }
    for (const {source, target} of edges) {
      const x = target.x - source.x;
      const y = target.y - source.y;
      const distance = Math.max(1, Math.hypot(x, y));
      const spring = (distance - 140) * 0.07 / distance;
      source.dx += x * spring;
      source.dy += y * spring;
      target.dx -= x * spring;
      target.dy -= y * spring;
    }
    const cooling = 1 - step / steps;
    for (const node of nodes) {
      node.x += node.dx * cooling;
      node.y += node.dy * cooling;
    }
  }
  // 标签按横向排版，给并排节点多留一点空间。
  for (const node of nodes) node.x *= 1.5;
}

class SpecGraph {
  /** 读取正式 Spec 数据并建立节点与连线，重复引用共享一条线。 */
  constructor(panel) {
    this.canvas = panel.querySelector("svg");
    this.world = panel.querySelector("[data-graph-world]");
    this.preview = panel.querySelector("[data-graph-preview]");
    const graph = JSON.parse(panel.dataset.specGraph);
    const nodes = new Map(graph.nodes.map((id) => [
      id, {id, contracts: graph.contracts[id], adjacent: new Set()},
    ]));
    this.nodes = [...nodes.values()];
    const nameCounts = new Map();
    for (const node of this.nodes) {
      node.name = node.id.split(":")[1];
      nameCounts.set(node.name, (nameCounts.get(node.name) || 0) + 1);
    }
    for (const node of this.nodes) {
      node.label = nameCounts.get(node.name) > 1 ? node.id : node.name;
    }
    this.edges = [];
    for (const [from, to] of graph.edges) {
      const source = nodes.get(from);
      const target = nodes.get(to);
      if (source.adjacent.has(target)) continue;
      source.adjacent.add(target);
      target.adjacent.add(source);
      this.edges.push({source, target});
    }

    layoutSpecGraph(this.nodes, this.edges);
    this.draw();
    this.placeLabels();
    this.fit();
    this.bind(panel);
  }

  /** 先画线，再画可点击、可用 Tab 聚焦的节点。 */
  draw() {
    for (const edge of this.edges) {
      const {source, target} = edge;
      edge.element = graphElement("line", {
        class: "spec-graph-edge",
        x1: source.x, y1: source.y, x2: target.x, y2: target.y,
      });
      this.world.append(edge.element);
    }
    for (const node of this.nodes) {
      const [type] = node.id.split(":");
      const radius = 5 + Math.min(9, Math.sqrt(node.adjacent.size) * 2.8);
      node.radius = radius;
      node.element = graphElement("a", {
        class: "spec-graph-node",
        href: "/?" + new URLSearchParams({spec: node.id}),
        transform: `translate(${node.x} ${node.y})`,
        "aria-label": node.id,
        "data-spec-type": type,
      });
      const label = graphElement("text");
      label.textContent = node.label;
      node.text = label;
      node.element.append(
        graphElement("circle", {r: Math.max(15, radius), class: "spec-graph-hit"}),
        graphElement("circle", {r: radius, class: "spec-graph-dot"}),
        label,
      );
      node.element.addEventListener("pointerenter", () => this.highlight(node));
      node.element.addEventListener("pointerleave", () => {
        if (document.activeElement !== node.element) this.highlight(null);
      });
      node.element.addEventListener("focus", () => this.highlight(node));
      node.element.addEventListener("blur", () => this.highlight(null));
      this.world.append(node.element);
    }
  }

  /** 用实际字体尺寸为标签寻找空位，拥挤时优先保留连接较多的节点。 */
  placeLabels() {
    const visible = this.nodes.filter(({element}) => !element.classList.contains("is-hidden"));
    const occupied = visible.map(({x, y, radius}) => ({
      x: x - radius - 3, y: y - radius - 3, width: 2 * radius + 6, height: 2 * radius + 6,
    }));
    for (const node of visible.sort((a, b) => b.adjacent.size - a.adjacent.size)) {
      const {x, y, radius, text} = node;
      text.setAttribute("x", "0");
      text.setAttribute("y", "0");
      const box = text.getBBox();
      const candidates = [
        [-box.width / 2, radius + 7],
        [-box.width / 2, -radius - box.height - 7],
        [radius + 8, -box.height / 2],
        [-radius - box.width - 8, -box.height / 2],
      ];
      // 四周都没有空位时只显示节点，完整名称仍可在预览中查看。
      const position = candidates.find(([left, top]) => !occupied.some((other) =>
        x + left < other.x + other.width + 4 && x + left + box.width + 4 > other.x &&
        y + top < other.y + other.height + 4 && y + top + box.height + 4 > other.y
      ));
      text.classList.toggle("is-crowded", !position);
      const [left, top] = position || candidates[0];
      text.setAttribute("x", left - box.x);
      text.setAttribute("y", top - box.y);
      if (position) occupied.push({x: x + left, y: y + top, width: box.width, height: box.height});
    }
  }

  /** 高亮关联节点及实际连线，以便从全图定位某个 Spec。 */
  highlight(active) {
    for (const node of this.nodes) {
      node.element.classList.toggle("is-active", node === active);
      node.element.classList.toggle(
        "is-muted", Boolean(active && node !== active && !active.adjacent.has(node)),
      );
    }
    for (const {source, target, element} of this.edges) {
      const incident = source === active || target === active;
      element.classList.toggle("is-active", incident);
      element.classList.toggle("is-muted", Boolean(active && !incident));
    }
    if (active) {
      // 保留最近的预览，方便把鼠标移过去滚动或复制完整引用。
      this.preview.querySelector("[data-graph-preview-name]").textContent = active.id;
      const items = active.contracts.map((reference) => {
        const item = document.createElement("li");
        item.textContent = reference;
        return item;
      });
      this.preview.querySelector("[data-graph-preview-contracts]").replaceChildren(...items);
      this.preview.hidden = false;
    }
  }

  /** 按图的实际边界和画布尺寸居中，给标签和连线留出边距。 */
  fit() {
    const {x, y, width, height} = this.world.getBBox();
    this.width = this.canvas.clientWidth;
    this.height = this.canvas.clientHeight;
    this.scale = Math.min(
      1.25, (this.width - 48) / Math.max(width, 1), (this.height - 48) / Math.max(height, 1),
    );
    this.minimumScale = this.scale * 0.5;
    this.x = this.width / 2 - (x + width / 2) * this.scale;
    this.y = this.height / 2 - (y + height / 2) * this.scale;
    this.updateCamera();
  }

  /** 让节点与连线共享同一个平移和缩放坐标系。 */
  updateCamera() {
    this.world.setAttribute("transform", `translate(${this.x} ${this.y}) scale(${this.scale})`);
    this.canvas.classList.toggle("is-zoomed-out", this.scale < 0.62);
  }

  /** 缩放时保持指针下方的节点停在原位。 */
  zoom(factor, x = this.width / 2, y = this.height / 2) {
    const next = Math.max(this.minimumScale, Math.min(3, this.scale * factor));
    const ratio = next / this.scale;
    this.x = x - (x - this.x) * ratio;
    this.y = y - (y - this.y) * ratio;
    this.scale = next;
    this.updateCamera();
  }

  /** 空白处接管拖动，节点保留浏览器原生的点击和打开链接行为。 */
  bind(panel) {
    let drag = null;
    this.canvas.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || event.target.closest("a")) return;
      this.preview.hidden = true;
      drag = {id: event.pointerId, x: event.clientX - this.x, y: event.clientY - this.y};
      this.canvas.setPointerCapture(event.pointerId);
      this.canvas.classList.add("is-dragging");
    });
    this.canvas.addEventListener("pointermove", (event) => {
      if (drag?.id !== event.pointerId) return;
      this.x = event.clientX - drag.x;
      this.y = event.clientY - drag.y;
      this.updateCamera();
    });
    this.canvas.addEventListener("lostpointercapture", () => {
      drag = null;
      this.canvas.classList.remove("is-dragging");
    });
    this.canvas.addEventListener("wheel", (event) => {
      event.preventDefault();
      const bounds = this.canvas.getBoundingClientRect();
      this.zoom(event.deltaY < 0 ? 1.12 : 1 / 1.12, event.clientX - bounds.left, event.clientY - bounds.top);
    }, {passive: false});

    // 图谱获得焦点时可通过方向键平移，通过加减键缩放。
    this.canvas.addEventListener("keydown", (event) => {
      const distance = event.shiftKey ? 96 : 32;
      switch (event.key) {
        case "Escape": this.preview.hidden = true; return;
        case "+": case "=": this.zoom(1.25); break;
        case "-": this.zoom(0.8); break;
        case "ArrowUp": this.y += distance; break;
        case "ArrowDown": this.y -= distance; break;
        case "ArrowLeft": this.x += distance; break;
        case "ArrowRight": this.x -= distance; break;
        default: return;
      }
      event.preventDefault();
      this.updateCamera();
    });
    for (const button of panel.querySelectorAll("[data-graph-zoom]")) {
      button.addEventListener("click", () => {
        switch (button.dataset.graphZoom) {
          case "reset": this.fit(); break;
          case "in": this.zoom(1.25); break;
          case "out": this.zoom(0.8); break;
        }
      });
    }
    const help = panel.querySelector("#graph-help");
    const instructions = help.textContent;
    panel.querySelector("[data-graph-isolates]").addEventListener("change", (event) => {
      for (const node of this.nodes) {
        node.element.classList.toggle("is-hidden", !event.target.checked && !node.adjacent.size);
      }
      help.textContent = event.target.checked || this.edges.length
        ? instructions : "当前正式 Spec 之间没有引用";
      this.preview.hidden = true;
      this.placeLabels();
      this.fit();
    });
    new ResizeObserver(() => this.fit()).observe(this.canvas);
  }
}

const graphPanel = document.querySelector("[data-spec-graph]");
if (graphPanel) document.fonts.ready.then(() => new SpecGraph(graphPanel));
