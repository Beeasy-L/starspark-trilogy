// 星火PPT · chart 字段链路运行时验证（node 沙箱跑 index.html 里的原函数）
// 用法: node tools/_tmp_verify_chart.js
// 只读：从 static/index.html 抠出原函数，在沙箱里跑，断言字段是否真的活过来。
const fs = require("fs");
const vm = require("vm");
const path = require("path");

const SRC = path.join(__dirname, "..", "产品", "星火PPT", "static", "index.html");
const html = fs.readFileSync(SRC, "utf8");

function grab(name) {
  const re = new RegExp("function\\s+" + name + "\\s*\\([^)]*\\)\\s*\\{", "g");
  const m = re.exec(html);
  if (!m) throw new Error("not found: " + name);
  let i = m.index + m[0].length - 1, depth = 0, inStr = null, esc = false;
  for (; i < html.length; i++) {
    const ch = html[i];
    if (inStr) {
      if (esc) esc = false;
      else if (ch === "\\") esc = true;
      else if (ch === inStr) inStr = null;
      continue;
    }
    if (ch === '"' || ch === "'" || ch === "`") inStr = ch;
    else if (ch === "{") depth++;
    else if (ch === "}") { depth--; if (depth === 0) break; }
  }
  return html.slice(m.index, i + 1);
}

const env = `
globalThis.XH_BLUEPRINTS = { report: { pages: [{ p: "结论页", m: "写清楚" }] } };
globalThis.SKILL_META = { report: { name: "职场报告", desc: "d" } };
globalThis.state = { doctor:null, slides:[], current:0, density:"auto", skill:"report", template:"t1",
                    refTexts:[], poemSeed:null, poemAssign:{}, poemUsedHalf:{}, poemCover:null, poemBack:null };
globalThis.$ = function(){ return { style:{setProperty:function(){}, width:""}, textContent:"", innerHTML:"", value:"",
                                     classList:{add:function(){},remove:function(){},contains:function(){return false;}},
                                     querySelector:function(){return null;}, querySelectorAll:function(){return [];} }; };
globalThis.renderStage = function(){ globalThis.__out = state.slides; };
globalThis.renderThumbs = function(){};
globalThis.renderSlide = function(){};
globalThis.clearError = function(){};
globalThis.toast = function(){};
`;

const sandbox = { console };
vm.createContext(sandbox);

const code = [
  grab("blueprintText"), grab("densityRule"), grab("buildUserPromptJS"),
  grab("normLayout"), grab("splitPair"), grab("normalizeSlide"),
  grab("buildDeck"), grab("chartItems"),
].join("\n\n");

let pass = 0, fail = 0;
function assert(name, cond, detail) {
  if (cond) { console.log("  ✅ " + name + (detail ? "  " + detail : "")); pass++; }
  else { console.log("  ❌ " + name + (detail ? "  " + detail : "")); fail++; }
}

console.log("=".repeat(70));
console.log("星火PPT · chart 字段链路运行时验证");
console.log("文件: " + SRC);
console.log("=".repeat(70));

try {
  vm.runInContext(env + code + `
    // 1) P0-1 复查：buildUserPromptJS 不应抛错
    globalThis.__prompt = buildUserPromptJS("原始文案", "report", 8, "");
    globalThis.__promptHasBP = __prompt.indexOf("页序骨架") >= 0;

    // 2) P0-2：AI 返回带 chart，buildDeck 后必须还在
    buildDeck({ title:"T", subtitle:"S", slides:[
      { title:"转化率", layout:"chart", content:[], note:"所以呢",
        chart:{ type:"ring", unit:"%", items:[{label:"转化率", value:75}] } }
    ]});
    globalThis.__slide = state.slides[0];
    globalThis.__items = chartItems(state.slides[0], state.slides[0].content);
  `, sandbox);

  console.log("\n[P0-1] 纯前端提示词构建");
  assert("buildUserPromptJS 不抛错", true, "len=" + String(sandbox.__prompt).length);
  assert("提示词含页序骨架", !!sandbox.__promptHasBP);

  console.log("\n[P0-2] chart 字段透传");
  const sl = sandbox.__slide;
  assert("buildDeck 后 chart 仍存在", !!(sl && sl.chart),
         sl && sl.chart ? JSON.stringify(sl.chart) : "chart=" + String(sl && sl.chart));
  assert("chart.type === 'ring'", sl && sl.chart && sl.chart.type === "ring");
  assert("chart.items[0].value === 75",
         sl && sl.chart && sl.chart.items && sl.chart.items[0].value === 75);

  console.log("\n[下游] 渲染器读到的数据");
  const items = sandbox.__items;
  assert("chartItems 返回真实条目", Array.isArray(items) && items.length === 1,
         JSON.stringify(items));
  assert("标签非空（不再是空串）",
         items && items.length === 1 && items[0].label === "转化率",
         items && items[0] ? JSON.stringify(items[0]) : "");
  assert("数值非 0（不再是 0 兜底）",
         items && items.length === 1 && items[0].value === 75);
} catch (e) {
  console.log("\n❌ 探针抛错: " + e.constructor.name + ": " + e.message);
  fail++;
}

console.log("\n" + "-".repeat(70));
console.log("通过 " + pass + " / 失败 " + fail);
console.log(fail === 0 ? "✅ chart 链路在运行时是活的" : "❌ chart 链路仍有断点");
process.exit(fail === 0 ? 0 : 1);
