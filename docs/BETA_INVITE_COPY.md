# 小范围 Beta 邀请文案 — 拿来即用

Iter #44 配合 SETUP_TURSO.md 完成后即可发出。三个版本（朋友圈短文案 / 私聊长版 / 邮件版），任选。

---

## 📱 朋友圈 / 微信群短版 (~150 字)

> 在测一个东西，**Omytea Console** — 帮你给真实人生决策（offer / 转方向 / 搬家 / 留学）打一个**带概率的预测**，3 个月后回来打分看你当时判断的校准度。不是算命，是**校准日记**。先到先 beta，桌面浏览器最好（手机能用但糙）。
>
> 链接：https://omytea-personal-console.streamlit.app/
>
> 试完发我反馈：哪里看不懂、哪里读起来像 AI 词、哪里你会真的拿来用。

---

## 💬 私聊长版 (~400 字)

> Hey，[名字]，我做了一个东西想拉你做 beta 测试一下，不超过 10 分钟。
>
> **它是什么**：Omytea Console — 用来给"接受这个 offer 还是换工作 / 搬家还是留在原地 / 读 PhD 还是去工业界"这种**真实人生决策**输出多个未来分支 + 各自概率。然后**3 个月后**你会收到日历提醒回来打分：当初的预测准不准。校准次数多了你就知道自己在哪类决策上系统性高估/低估什么。
>
> **不是算命**。我把它叫"校准决策日记"。底层是一个量子启发的世界模型 (technical 部分你完全可以不看)，前端是张概率热力图 + 几个候选分支的叙事 + 一个"为什么是这个概率"的下钻。
>
> **试用方法**：
> 1. 打开 https://omytea-personal-console.streamlit.app/ — 用电脑浏览器，手机能用但体验糙
> 2. 看完顶部的 beta 提示（数据存在 demo 服务器、不要粘敏感信息），点"Got it — continue"
> 3. 选一个 chip（"接 offer 还是留"/"搬家"/"PhD 还是工业界"），改成你自己的决策 → "See my futures →"
> 4. 结果页顶部有三个按钮：**Add calendar** 加日历提醒、**复制 prediction ID**、**Save snapshot** 下个 .json 留底
> 5. **请把 prediction ID 截图保存**（要是 demo 服务器挂了我能用 .json 帮你恢复）
> 6. 3 个月后回来打分（日历会提醒你）
>
> **我想要的反馈**（不需要长，一句话也行）：
> - 哪里看不懂 / 读起来像 dev / 像 AI 词
> - 哪个分支的叙事让你觉得"这不是我会真的考虑的"
> - 你**真的会拿它来做决策**吗？什么阻止你
> - 移动端有没有炸的地方
>
> 别太客气，骂得越狠越值钱 🙏

---

## ✉️ 邮件版

**Subject**: 10-min beta — Omytea Console (calibrated decision journal)

Hi [Name],

I'm running a tiny beta of **Omytea Console**, a calibrated decision journal for personal-life decisions (job offers, relocations, PhD-vs-industry calls). It takes ~5 minutes to use and ~3 months to find out if it worked.

**The idea**: you describe a real decision → it generates 3-5 future scenarios with calibrated probabilities + a one-line story for each → 3 months later you come back and score how reality matched. Over enough predictions you find out where you systematically over- or under-confide.

It's **not fortune-telling**. The "玄学透镜" easter egg exists but is opt-in.

**Try it** (best on desktop, mobile usable but rough):

1. https://omytea-personal-console.streamlit.app/
2. Read the "Research beta" banner, click "Got it — continue"
3. Pick a starter chip, edit to your real decision, hit "See my futures →"
4. On the result page, the top row has: **📅 Add to calendar**, your prediction ID (hover to copy), **Score later →**, **💾 Save snapshot**
5. **Save the prediction ID + download the .json** (the demo server's storage is durable now via Turso, but the .json is your personal copy for safety)
6. The calendar reminder will ping you in ~3 months

**Feedback** (one line is fine):
- What's confusing or reads as dev-jargon?
- Would you actually use this for real decisions? What stops you?
- Any mobile rendering bugs?

Thanks for testing — even harsh feedback is gold.

— [Founder name]

---

## 🚨 What to send when something breaks

If a tester reports a crash / wrong number / weird copy:

1. Ask for their **prediction ID** (8-char prefix is enough).
2. Ask for a **screenshot** (1 PNG > 100 words of bug description).
3. Ask if they downloaded the **.json snapshot** — if yes, request it.
4. Log to `.wolf/buglog.json` per OpenWolf protocol.
5. If data loss is suspected: check Turso via `turso db shell omytea-personal-console "SELECT * FROM predictions WHERE prediction_id LIKE '<prefix>%';"`.

---

## ⚙️ Pre-send checklist (founder)

Run through once before sending the first invite:

- [ ] SETUP_TURSO.md steps 1-5 done; Turso DB live + [turso] block in Streamlit Cloud Secrets
- [ ] Live demo loads at https://omytea-personal-console.streamlit.app/?embed=true
- [ ] Make a test prediction; note the ID
- [ ] Reboot Streamlit Cloud from share.streamlit.io
- [ ] Revisit the demo; Measurement Update → paste the test ID — **prediction survives** ✓
- [ ] If not: SETUP_TURSO.md troubleshooting (check `[storage] WARNING` line in logs)
- [ ] PRIVACY_POLICY.md mentions Turso as the "demo server" (small TODO, low-priority)
- [ ] Pick 3-5 friends, NOT 20 — small-batch beta = high-signal feedback

Once that box is ticked, **send**.
