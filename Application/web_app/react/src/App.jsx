import { useEffect, useState } from "react";
import { initializeSignaController } from "./signaController.js";
import "./App.css";

export default function App() {
  const [activePage, setActivePage] = useState("signPage");

  useEffect(() => initializeSignaController(), []);

  return (
    <>
<main className={"shell"}>
      <header className={"topbar"}>
      <div className={"brand"}>
      <div className={"mark"} aria-hidden={"true"}>S</div>
      <span>SIGNA</span>
      </div>
      <div className={"top-note"}>
      <i className={"dot"}>
      </i> Bidirectional ISL communication</div>
      </header>
      <section className={"hero"}>
      <div>
      <div className={"eyebrow"}>Sign to conversation</div>
      <h1>Make every sign<br />part of the conversation.</h1>
      <p>A guided flow for checking the audience profile, recognizing signs live, reviewing the sentence, and sharing a clear message.</p>
      </div>
      <div className={"session-tag"}>● &nbsp;Live inference · no video saved</div>
      </section>
      <section className={"status-strip"} aria-label={"System status"}>
      <div className={"status-chip"} id={"cameraStatus"}>
      <i>
      </i>Camera · disconnected</div>
      <div className={"status-chip"} id={"framesStatus"}>
      <i>
      </i>Frames · 0 received / 0 decoded</div>
      <div className={"status-chip"} id={"handsStatus"}>
      <i>
      </i>Hand landmarks · waiting</div>
      <div className={"status-chip"} id={"poseStatus"}>
      <i>
      </i>Pose landmarks · waiting</div>
      <div className={"status-chip ok"} id={"modelStatus"}>
      <i>
      </i>Model · loaded</div>
      <div className={"status-chip"} id={"micStatus"}>
      <i>
      </i>Microphone · idle</div>
      <div className={"status-chip"} id={"outputStatus"}>
      <i>
      </i>Output · browser available</div>
      </section>
      <nav className={"steps"} aria-label={"Conversation steps"}>
      <div className={"step active"} data-step={"1"}>
      <span className={"num"}>1</span>Audience setup</div>
      <div className={"step"} data-step={"2"}>
      <span className={"num"}>2</span>Live signs</div>
      <div className={"step"} data-step={"3"}>
      <span className={"num"}>3</span>Review sentence</div>
      <div className={"step"} data-step={"4"}>
      <span className={"num"}>4</span>Share message</div>
      </nav>
      <nav className={"app-tabs"} aria-label={"Communication direction"}>
      <button className={activePage === "signPage" ? "app-tab active" : "app-tab"} data-page={"signPage"} onClick={() => setActivePage("signPage")}>Sign → Speech</button>
      <button className={activePage === "speechPage" ? "app-tab active" : "app-tab"} data-page={"speechPage"} onClick={() => setActivePage("speechPage")}>Speech → Sign</button>
      <button className={activePage === "testPage" ? "app-tab active" : "app-tab"} data-page={"testPage"} onClick={() => setActivePage("testPage")}>Testing &amp; setup</button>
    </nav>
      <section className={activePage === "signPage" ? "page-panel active" : "page-panel"} id={"signPage"}>
      <div className={"layout"}>
      <section className={"card camera-card"}>
      <div className={"card-head"}>
      <div>
      <h2>Camera &amp; signing area</h2>
      <p className={"sub"}>Keep your face, shoulders, and hands visible in the frame.</p>
      </div>
      <div className={"live-pill"} id={"livePill"}>
      <i className={"dot"}>
      </i>
      <span id={"liveText"}>Camera off</span>
      </div>
      </div>
      <div className={"stream-row"}>
      <div className={"stream-field"}>
      <label htmlFor={"streamUrl"}>Camera live-stream URL</label>
      <input id={"streamUrl"} type={"url"} defaultValue={""} spellCheck={"false"} />
      </div>
      <a className={"stream-link"} id={"cameraStatusLink"} href={"http://192.168.0.105/status"} target={"_blank"} rel={"noreferrer"}>Camera status ↗</a>
      </div>
      <div className={"preview"} id={"preview"}>
      <img id={"networkStream"} alt={"Live camera stream"} />
      <div className={"placeholder"}>
      <div className={"camera-icon"}>◉</div>
      <strong>Your camera preview appears here</strong>
      <span>Connect to the camera stream when you are ready.</span>
      </div>
      <div className={"cam-status"}>
      <i className={"dot"}>
      </i>
      <span id={"camStatusLabel"}>Live stream</span>
      </div>
      </div>
      <div className={"under-preview"}>
      <span className={"small-note"} id={"cameraNote"}>Stream is displayed in the browser and is not saved by this prototype.</span>
      <button className={"btn primary"} id={"cameraBtn"}>Connect camera</button>
      </div>
      <section className={"diagnostic-panel"} aria-live={"polite"} aria-label={"Live camera and landmark diagnostics"}>
      <div className={"diagnostic-head"}>
      <strong>Live camera diagnostics</strong>
      <span>Preview overlay · landmarks are drawn only when detected</span>
      </div>
      <div className={"diagnostic-grid"}>
      <div className={"diag-cell"}>
      <b>Camera</b>
      <span className={"diag-status"} id={"diagCamera"}>Disconnected</span>
      </div>
      <div className={"diag-cell"}>
      <b>Frames</b>
      <span id={"diagFrames"}>0 received · 0 decoded</span>
      </div>
      <div className={"diag-cell"}>
      <b>Landmarks</b>
      <span id={"diagLandmarks"}>0 hand frames · 0 pose detections</span>
      </div>
      <div className={"diag-cell"}>
      <b>Model</b>
      <span className={"diag-status ok"} id={"diagModel"}>Phase 2 model loaded</span>
      </div>
      <div className={"diag-cell diag-wide"}>
      <b>Latest frame → MediaPipe input</b>
      <span id={"diagInput"}>Waiting for camera</span>
      </div>
      <div className={"diag-cell diag-wide"}>
      <b>Task configuration</b>
      <span id={"diagTasks"}>Not started</span>
      </div>
      <div className={"diag-cell diag-wide"}>
      <b>Landmark errors</b>
      <span id={"diagErrors"}>0 errors</span>
      </div>
      <div className={"diag-cell diag-wide"}>
      <b>Frame orientation</b>
      <span id={"diagOrientation"}>Raw camera orientation; no mirroring or rotation applied.</span>
      </div>
      </div>
      </section>
      <div className={"notice"}>
      <strong>Live model:</strong> this page uses the Phase 2 pilot through a local Python service. Frames stay in a short rolling memory buffer and are discarded; no video file is created. The model recognizes its eight trained labels only.</div>
      </section>
      <aside className={"right-col"}>
      <section className={"card flow-card"}>
      <div className={"card-head"}>
      <div>
      <h2>1 · Age calibration</h2>
      <p className={"sub"}>Starts with the camera and locks after 10 seconds; age inference then stops.</p>
      </div>
      </div>
      <div className={"age-box"}>
      <div className={"age-row"}>
      <div>
      <div className={"label"}>MiVOLO age estimate</div>
      <div className={"age-value"} id={"ageValue"}>Waiting</div>
      <div className={"age-desc"} id={"ageDesc"}>Connect camera to load face/person models.</div>
      </div>
      <div className={"timer"} id={"timer"}>
      <span id={"timerText"}>—</span>
      </div>
      </div>
      <div className={"btn-row"}>
      <button className={"btn ghost"} id={"skipAgeBtn"} disabled={true}>Continue with age unknown</button>
      </div>
      <div className={"select-wrap"}>
      <label htmlFor={"audience"}>Audience wording style · choose or adjust</label>
      <select defaultValue="standard" id={"audience"}>
      <option value={"simple"}>Simple and direct</option>
      <option value={"standard"}>Everyday</option>
      <option value={"detailed"}>More context</option>
      </select>
      <p className={"hint"}>Age is only a rough model estimate. Wording remains user-adjustable; age alone does not determine comprehension.</p>
      </div>
      </div>
      </section>
      <section className={"card record-card"}>
      <div className={"rec-top"}>
      <div>
      <h2 className={"section-title"}>2 · Live sign recognition</h2>
      <p className={"sub"}>The pretrained model checks a rolling camera window in memory. Nothing is recorded to disk.</p>
      </div>
      <span className={"record-state"} id={"recordState"}>Waiting</span>
      </div>
      <div className={"record-control"}>
      <i className={"record-dot"} id={"recognitionDot"}>
      </i>
      <div className={"record-copy"}>
      <strong id={"recordTitle"}>Waiting for live camera</strong>
      <span id={"recordHelp"}>Connect the camera to start live inference.</span>
      </div>
      </div>
      <div className={"record-state"} id={"modelScore"}>No decision score yet</div>
      <div className={"divider"}>
      </div>
      <div className={"label"}>Pretrained vocabulary · 8 signs</div>
      <div className={"labels"} id={"labels"}>
      </div>
      <div className={"divider"}>
      </div>
      <div className={"rec-top"}>
      <span className={"record-copy"}>
      <strong id={"candidateText"}>No stable suggestion yet</strong>
      <span id={"candidateHelp"}>A sign suggestion appears after the model sees a stable pattern.</span>
      </span>
      <button className={"btn secondary"} id={"addBtn"} disabled={true}>Add suggestion</button>
      </div>
      </section>
      <section className={"card record-card"}>
      <div className={"card-head"}>
      <div>
      <h2>3 · Review &amp; share</h2>
      <p className={"sub"}>Confirm each label before it becomes part of the message.</p>
      </div>
      </div>
      <div className={"sent-labels"} id={"sentLabels"}>
      </div>
      <div className={"sentence empty"} id={"sentence"}>Wait for a live sign suggestion and confirm it to start a sentence.</div>
      <div className={"btn-row"}>
      <button className={"btn ghost"} id={"undoBtn"} disabled={true}>Undo</button>
      <button className={"btn ghost"} id={"clearBtn"} disabled={true}>Clear sentence</button>
      <button className={"btn secondary"} id={"finishBtn"} disabled={true}>Finish sentence</button>
      </div>
      <div className={"divider"}>
      </div>
      <div className={"output"}>
      <div className={"label"}>Message preview</div>
      <div className={"out-text"} id={"outputText"}>No supported sentence yet.</div>
      <div className={"out-foot"}>
      <span id={"styleLabel"}>Everyday wording</span>
      <div>
      <button className={"copy-btn"} id={"copyBtn"} disabled={true}>Copy</button>
      {' '}
      <button className={"copy-btn"} id={"speakBtn"} disabled={true}>Speak</button>
      </div>
      </div>
      </div>
      <div className={"hardware-row"}>
      <input id={"signaBase"} type={"url"} placeholder={"Display ESP32 base URL (optional)"} />
      <button className={"btn ghost"} id={"sendButton"} disabled={true}>Send to display</button>
      </div>
      <p className={"hint"} id={"hardwareStatus"}>Transmission needs a configured display controller; success requires its HTTP acknowledgement.</p>
      <div className={"divider"}>
      </div>
      <div className={"label"}>Finished sentence history</div>
      <div className={"history-list"} id={"historyList"}>
      </div>
      </section>
      </aside>
      </div>
      </section>
      <section className={activePage === "speechPage" ? "page-panel active" : "page-panel"} id={"speechPage"}>
      <div className={"layout"}>
      <section className={"card wide-card"}>
      <div className={"card-head"}>
      <div>
      <h2>Speech → sign display</h2>
      <p className={"sub"}>Speak or type. Only phrases covered by the current vocabulary are mapped; missing sign videos stay clearly marked.</p>
      </div>
      <div className={"live-pill"} id={"speechState"}>
      <i className={"dot"}>
      </i>
      <span>Microphone idle</span>
      </div>
      </div>
      <div className={"btn-row"}>
      <button className={"btn primary"} id={"listenBtn"}>Start listening</button>
      <button className={"btn ghost"} id={"stopListenBtn"} disabled={true}>Stop</button>
      <button className={"btn ghost"} id={"clearSpeechBtn"}>Clear</button>
      </div>
      <p className={"hint"}>Speech recognition uses your browser's speech service where available; the browser may process audio using its configured provider. SIGNA does not save audio.</p>
      <div className={"select-wrap"}>
      <label htmlFor={"speechText"}>Recognized or manually entered speech</label>
      <textarea className={"speech-box"} id={"speechText"} placeholder={"Try: Hello, Thank you, Where are you going?, or I will go to school tomorrow."}>
      </textarea>
      </div>
      <div className={"btn-row"}>
      <button className={"btn secondary"} id={"mapSpeechBtn"}>Show supported signs</button>
      </div>
      </section>
      <section className={"card wide-card"}>
      <div className={"card-head"}>
      <div>
      <h2>Sign representation</h2>
      <p className={"sub"} id={"signMapStatus"}>No sign assets are bundled yet.</p>
      </div>
      </div>
      <div className={"sent-labels"} id={"speechGlosses"}>
      </div>
      <div className={"asset-placeholder"} id={"assetDisplay"}>Supported text can map to gloss labels. Supply verified ISL sign clips to show a genuine visual representation.</div>
      <div className={"history-list"} id={"unsupportedWords"}>
      </div>
      </section>
      </div>
      </section>
      <section className={activePage === "testPage" ? "page-panel active" : "page-panel"} id={"testPage"}>
      <div className={"layout"}>
      <section className={"card wide-card"}>
      <div className={"card-head"}>
      <div>
      <h2>Live camera tests · eight model labels</h2>
      <p className={"sub"}>Start a test, perform one sign, and let the live model produce a stable prediction. Manual input never counts here.</p>
      </div>
      <span className={"session-tag"} id={"testSummary"}>0 passed · 0 failed · 8 not tested</span>
      </div>
      <div className={"test-grid"} id={"wordTests"}>
      </div>
      <p className={"notice"}>
      <strong>Scoring:</strong> pass requires an actual live stabilized model label equal to the expected label. This Ridge model does not output calibrated probabilities; the UI shows an uncalibrated decision-score margin instead of presenting it as confidence.</p>
      </section>
      <section className={"card wide-card"}>
      <div className={"card-head"}>
      <div>
      <h2>Sentence rule checks</h2>
      <p className={"sub"}>These checks exercise the existing sentence composer and are separate from camera tests.</p>
      </div>
      <button className={"btn secondary"} id={"runSentenceTests"}>Run sentence checks</button>
      </div>
      <div className={"history-list"} id={"sentenceTestResults"}>
      </div>
      <div className={"divider"}>
      </div>
      <div className={"label"}>Manual sentence test · never counted as live recognition</div>
      <div className={"hardware-row"}>
      <input id={"manualLabels"} placeholder={"Example: I TOMORROW SCHOOL GO"} />
      <button className={"btn ghost"} id={"manualCompose"}>Preview</button>
      </div>
      <div id={"manualResult"} className={"test-result"}>Type supported gloss labels to check an existing rule.</div>
      </section>
      </div>
      </section>
      <footer className={"footer"}>
      <span>Live sign classifier: 8 labels · signer-held-out accuracy 83.3% (24 clips)</span>
      <span>Model evaluated on isolated clips; live-stream accuracy remains unmeasured</span>
      </footer>
      </main>
      <div className={"toast"} id={"toast"} role={"status"} aria-live={"polite"}>
      </div>
    </>
  );
}
