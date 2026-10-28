import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";

const ROOT_ID = "uruha-vrm-viewer-p4";
const MAX_FILE_BYTES = 100 * 1024 * 1024;
const FLOW_IDS = [
  "local_asset_selected",
  "local_asset_validated",
  "vrm_parsed",
  "vrm_rendered",
];

function installStyles() {
  if (document.getElementById(`${ROOT_ID}-style`)) return;
  const style = document.createElement("style");
  style.id = `${ROOT_ID}-style`;
  style.textContent = `
    #${ROOT_ID}{position:fixed;right:18px;bottom:18px;width:min(390px,calc(100vw - 36px));z-index:10020;
      color:#f7f4ff;font:13px/1.45 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      background:linear-gradient(160deg,rgba(20,18,32,.97),rgba(9,13,24,.98));border:1px solid rgba(172,141,255,.42);
      border-radius:20px;box-shadow:0 22px 70px rgba(0,0,0,.48);overflow:hidden;backdrop-filter:blur(18px)}
    #${ROOT_ID}[data-collapsed="true"] .uv-body{display:none}
    #${ROOT_ID} .uv-head{display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid rgba(255,255,255,.09)}
    #${ROOT_ID} .uv-orb{width:11px;height:11px;border-radius:50%;background:#62e6bb;box-shadow:0 0 18px #62e6bb}
    #${ROOT_ID} .uv-title{font-weight:760;letter-spacing:.02em;flex:1}
    #${ROOT_ID} .uv-badge{font-size:10px;color:#bca8ff;background:rgba(154,117,255,.13);border:1px solid rgba(170,140,255,.28);padding:3px 7px;border-radius:999px}
    #${ROOT_ID} button{font:inherit;color:inherit}
    #${ROOT_ID} .uv-toggle{border:0;background:transparent;cursor:pointer;font-size:16px;padding:2px 5px}
    #${ROOT_ID} .uv-stage{position:relative;height:286px;background:radial-gradient(circle at 50% 30%,#292444 0,#101321 52%,#070a11 100%)}
    #${ROOT_ID} canvas{display:block;width:100%;height:100%}
    #${ROOT_ID} .uv-watermark{position:absolute;left:12px;top:10px;color:rgba(255,255,255,.54);font-size:10px;letter-spacing:.08em}
    #${ROOT_ID} .uv-state{position:absolute;left:12px;right:12px;bottom:10px;padding:8px 10px;border-radius:10px;background:rgba(7,9,16,.74);border:1px solid rgba(255,255,255,.09)}
    #${ROOT_ID} .uv-state strong{display:block;color:#fff;font-size:12px}
    #${ROOT_ID} .uv-state span{display:block;color:#aaa9b8;font-size:10px;margin-top:2px}
    #${ROOT_ID} .uv-flow{display:grid;grid-template-columns:repeat(4,1fr);gap:5px;padding:11px 12px 8px}
    #${ROOT_ID} .uv-node{position:relative;min-height:45px;padding:7px 5px;border:1px solid rgba(255,255,255,.1);border-radius:9px;color:#858697;background:rgba(255,255,255,.025);text-align:center;font-size:9px}
    #${ROOT_ID} .uv-node::before{content:"";display:block;width:7px;height:7px;margin:0 auto 4px;border-radius:50%;background:#50515d}
    #${ROOT_ID} .uv-node[data-state="active"]{color:#f2ecff;border-color:#a884ff;background:rgba(168,132,255,.12)}
    #${ROOT_ID} .uv-node[data-state="active"]::before{background:#b392ff;box-shadow:0 0 10px #b392ff}
    #${ROOT_ID} .uv-node[data-state="done"]{color:#bdffe9;border-color:rgba(98,230,187,.42)}
    #${ROOT_ID} .uv-node[data-state="done"]::before{background:#62e6bb}
    #${ROOT_ID} .uv-node[data-state="error"]{color:#ffb8c2;border-color:rgba(255,95,120,.48)}
    #${ROOT_ID} .uv-node[data-state="error"]::before{background:#ff5f78}
    #${ROOT_ID} .uv-controls{display:flex;gap:8px;padding:3px 12px 12px}
    #${ROOT_ID} .uv-pick,#${ROOT_ID} .uv-clear{display:inline-flex;align-items:center;justify-content:center;min-height:34px;border-radius:10px;cursor:pointer}
    #${ROOT_ID} .uv-pick{flex:1;background:linear-gradient(135deg,#8c68ee,#604ac7);font-weight:720;padding:0 12px}
    #${ROOT_ID} .uv-pick input{display:none}
    #${ROOT_ID} .uv-clear{width:74px;border:1px solid rgba(255,255,255,.15);background:rgba(255,255,255,.04)}
    #${ROOT_ID} .uv-meta{padding:0 12px 12px;color:#878896;font-size:10px}
    #${ROOT_ID} .uv-meta b{color:#bbb7c9;font-weight:650}
  `;
  document.head.appendChild(style);
}

function createPanel() {
  const root = document.createElement("aside");
  root.id = ROOT_ID;
  root.dataset.status = "waiting_for_local_vrm";
  root.dataset.collapsed = "false";
  root.innerHTML = `
    <div class="uv-head">
      <span class="uv-orb"></span><span class="uv-title">Local VRM Stage</span>
      <span class="uv-badge">browser only</span><button class="uv-toggle" type="button" aria-label="collapse">⌄</button>
    </div>
    <div class="uv-body">
      <div class="uv-stage"><canvas></canvas><div class="uv-watermark">NEUTRAL STAGE · NOT URUHA</div>
        <div class="uv-state"><strong>本機 3D 舞台已就緒</strong><span>尚未載入 VRM；下方流程沒有假裝完成。</span></div>
      </div>
      <div class="uv-flow">
        <div class="uv-node" data-node="local_asset_selected">選擇本機檔案</div>
        <div class="uv-node" data-node="local_asset_validated">格式與大小檢查</div>
        <div class="uv-node" data-node="vrm_parsed">VRM 解析</div>
        <div class="uv-node" data-node="vrm_rendered">畫面呈現</div>
      </div>
      <div class="uv-controls">
        <label class="uv-pick">選擇本機 .vrm<input type="file" accept=".vrm"></label>
        <button class="uv-clear" type="button">清除</button>
      </div>
      <div class="uv-meta"><b>隱私邊界：</b>檔案只在這個瀏覽器分頁解析，不上傳、不寫入伺服器。模型權利仍由提供者確認。</div>
    </div>`;
  document.body.appendChild(root);
  return root;
}

function installViewer(root) {
  const canvas = root.querySelector("canvas");
  const stage = root.querySelector(".uv-stage");
  const stateTitle = root.querySelector(".uv-state strong");
  const stateDetail = root.querySelector(".uv-state span");
  const fileInput = root.querySelector("input[type=file]");
  const clearButton = root.querySelector(".uv-clear");
  const toggleButton = root.querySelector(".uv-toggle");
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 40);
  camera.position.set(0, 1.35, 3.1);
  camera.lookAt(0, 1.05, 0);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x3a3158, 2.15));
  const key = new THREE.DirectionalLight(0xffffff, 2.3);
  key.position.set(1.4, 2.7, 2.2);
  scene.add(key);
  const grid = new THREE.GridHelper(4, 20, 0x6c5f98, 0x27283c);
  scene.add(grid);

  const placeholder = new THREE.Group();
  const wire = new THREE.MeshBasicMaterial({ color: 0x9b80ef, wireframe: true, transparent: true, opacity: 0.48 });
  const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.28, 0.72, 5, 12), wire);
  torso.position.y = 1.15;
  const head = new THREE.Mesh(new THREE.IcosahedronGeometry(0.25, 2), wire);
  head.position.y = 1.92;
  placeholder.add(torso, head);
  scene.add(placeholder);

  let currentVrm = null;
  let currentObjectUrl = null;
  let lastTime = performance.now();
  let firstRenderedFrame = false;

  function setFlow(completed, active = null, failed = null) {
    FLOW_IDS.forEach((id, index) => {
      const node = root.querySelector(`[data-node="${id}"]`);
      node.dataset.state = failed === id ? "error" : active === id ? "active" : index < completed ? "done" : "idle";
    });
  }

  function setStatus(status, title, detail) {
    root.dataset.status = status;
    stateTitle.textContent = title;
    stateDetail.textContent = detail;
  }

  function revokeObjectUrl() {
    if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl);
    currentObjectUrl = null;
  }

  function disposeMaterial(material) {
    if (!material) return;
    const rows = Array.isArray(material) ? material : [material];
    rows.forEach((row) => {
      Object.values(row).forEach((value) => {
        if (value && value.isTexture && typeof value.dispose === "function") value.dispose();
      });
      if (typeof row.dispose === "function") row.dispose();
    });
  }

  function unloadVrm() {
    revokeObjectUrl();
    if (!currentVrm) return;
    scene.remove(currentVrm.scene);
    currentVrm.scene.traverse((object) => {
      if (object.geometry && typeof object.geometry.dispose === "function") object.geometry.dispose();
      disposeMaterial(object.material);
    });
    VRMUtils.deepDispose(currentVrm.scene);
    currentVrm = null;
  }

  function fail(node, title, detail) {
    unloadVrm();
    placeholder.visible = true;
    firstRenderedFrame = false;
    setFlow(FLOW_IDS.indexOf(node), null, node);
    setStatus("load_failed", title, detail);
  }

  function validateFile(file) {
    if (!file || typeof file.name !== "string" || !file.name.toLowerCase().endsWith(".vrm")) {
      return "只接受副檔名為 .vrm 的本機檔案。";
    }
    if (!Number.isFinite(file.size) || file.size <= 0) return "檔案是空的，沒有進行解析。";
    if (file.size > MAX_FILE_BYTES) return "檔案超過 100 MB 上限，沒有進行解析。";
    return null;
  }

  function loadFile(file) {
    unloadVrm();
    placeholder.visible = true;
    firstRenderedFrame = false;
    setStatus("validating_local_file", "正在驗證本機檔案", "只檢查 .vrm、副檔名與 100 MB 大小上限。 ");
    setFlow(0, "local_asset_selected");
    const validationError = validateFile(file);
    if (validationError) {
      fail("local_asset_selected", "本機檔案未通過檢查", validationError);
      return;
    }
    setFlow(1, "local_asset_validated");
    setStatus("loading_vrm", "正在本機解析 VRM", "檔案不會傳到 UruhaBrain server。 ");
    currentObjectUrl = URL.createObjectURL(file);
    const manager = new THREE.LoadingManager();
    manager.setURLModifier((url) => {
      if (url.startsWith("blob:") || url.startsWith("data:")) return url;
      throw new Error("external_resource_blocked");
    });
    const loader = new GLTFLoader(manager);
    loader.register((parser) => new VRMLoaderPlugin(parser));
    loader.load(
      currentObjectUrl,
      (gltf) => {
        revokeObjectUrl();
        const vrm = gltf?.userData?.vrm;
        if (!vrm || !vrm.scene) {
          fail("vrm_parsed", "VRM 解析失敗", "檔案沒有可用的 VRM runtime 資料。 ");
          return;
        }
        currentVrm = vrm;
        VRMUtils.rotateVRM0(vrm);
        placeholder.visible = false;
        scene.add(vrm.scene);
        setFlow(3, "vrm_rendered");
        setStatus("loading_vrm", "VRM 已解析，正在確認畫面", "只有實際畫出一幀後才會標記完成。 ");
      },
      undefined,
      () => fail("vrm_parsed", "VRM 載入失敗", "解析器拒絕此檔案；沒有宣稱已顯示。")
    );
  }

  function clear() {
    unloadVrm();
    placeholder.visible = true;
    fileInput.value = "";
    firstRenderedFrame = false;
    setFlow(0);
    setStatus("waiting_for_local_vrm", "本機 3D 舞台已就緒", "尚未載入 VRM；下方流程沒有假裝完成。 ");
  }

  function resize() {
    const width = Math.max(1, stage.clientWidth);
    const height = Math.max(1, stage.clientHeight);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function animate(now) {
    const delta = Math.min((now - lastTime) / 1000, 0.1);
    lastTime = now;
    if (currentVrm) currentVrm.update(delta);
    if (placeholder.visible) placeholder.rotation.y += delta * 0.22;
    renderer.render(scene, camera);
    if (currentVrm && !firstRenderedFrame) {
      firstRenderedFrame = true;
      setFlow(4);
      const modelName = currentVrm.meta?.name ? String(currentVrm.meta.name) : "名稱未提供";
      setStatus("rendering_vrm", "VRM 已在本機畫面呈現", `模型資訊：${modelName}。未連接動作決策。`);
    }
    requestAnimationFrame(animate);
  }

  fileInput.addEventListener("change", () => loadFile(fileInput.files?.[0]));
  clearButton.addEventListener("click", clear);
  toggleButton.addEventListener("click", () => {
    const collapsed = root.dataset.collapsed === "true";
    root.dataset.collapsed = collapsed ? "false" : "true";
    toggleButton.textContent = collapsed ? "⌄" : "⌃";
    if (collapsed) requestAnimationFrame(resize);
  });
  new ResizeObserver(resize).observe(stage);
  resize();
  requestAnimationFrame(animate);

  return {
    loadFile,
    clear,
    getSnapshot: () => ({
      status: root.dataset.status,
      flow: FLOW_IDS.map((id) => ({ id, state: root.querySelector(`[data-node="${id}"]`).dataset.state || "idle" })),
      vrmLoaded: Boolean(currentVrm),
      objectUrlRetained: Boolean(currentObjectUrl),
      serverUploadCount: 0,
      actionExecutionCount: 0,
    }),
  };
}

function boot() {
  if (document.getElementById(ROOT_ID)) return;
  installStyles();
  const root = createPanel();
  window.__URUHA_VRM_P4__ = installViewer(root);
  window.dispatchEvent(new CustomEvent("uruha-vrm-p4-ready"));
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
  boot();
}
