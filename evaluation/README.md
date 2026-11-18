# Volunteer study E5

Status:10 user-supplied consenting feedback records validated and analysed. See responses/ and volunteer_results.json. P10 reported4/5 tasks; total49/50.

Recruit 6–10 consenting volunteer students yourself. Give each an anonymous code P01…P10. Run the project and open `/evaluation.html`. Participants complete the five tasks, download their feedback JSON, and voluntarily share that file with the team. Do not collect third-party transcripts or identity/grades. Keep each student's transcript on their own machine.

Put only consenting feedback JSON files in a local folder, then run:

`python evaluation/analyse_feedback.py /path/to/feedback`

The tool rejects duplicate participant codes and invalid scores; records sample count, correctness/unsure responses, usefulness mean and95% bootstrap CI, and task completion. Fewer than6 participants is marked incomplete. Test data must never be included as volunteer responses. No feedback responses are bundled in the release.
