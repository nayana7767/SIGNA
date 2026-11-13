# ISL sign display assets

The app currently has no verified sign videos, animations, or images. It intentionally shows a missing-asset message rather than substituting ASL or inventing an ISL handshape.

To add an asset, place a signer-approved clip at `assets/signs/<GLOSS>.mp4`, then update `manifest.json` with its relative file path, source/permission details, and `verified: true`. Suggested source video format: MP4/H.264, landscape or portrait, one clearly visible signer, hands and upper body in frame, short loop, no audio unless it is needed for the demonstration. Have an ISL-fluent reviewer confirm the sign variant and regional context before enabling the asset.

Required filenames for the current model vocabulary: `GO.mp4`, `HELLO.mp4`, `I.mp4`, `SCHOOL.mp4`, `THANK_YOU.mp4`, `TOMORROW.mp4`, `WHERE.mp4`, and `YOU.mp4`.
