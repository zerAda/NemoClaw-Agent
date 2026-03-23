name: career_agent
description: >
  Autonomous job hunting tool. Use this skill to run a job search and scoring
  cycle, retrieve current application pipeline status, or verify the career
  agent is running. The career agent scrapes job listings, scores them against
  the candidate profile in /app/brain/Bio_Context.md, and generates tailored
  cover letters for high-scoring matches.
tools:
  - name: run_cycle
    description: >
      Start a job search, scoring, and cover letter generation cycle.
      Call when the user asks to search for jobs, run the career agent,
      or trigger Phoenix. Returns immediately (202) — cycle runs in background.
    method: POST
    url: http://career-agent:8001/run-cycle
    parameters:
      keyword:
        type: string
        required: true
        description: "Job title or keyword to search for (e.g. 'AI Engineer', 'Backend Developer')"
      location:
        type: string
        required: false
        default: "France"
        description: "Target job location"

  - name: health_check
    description: >
      Verify the career agent sidecar is running and ready to accept requests.
      Call before run_cycle if you are unsure the service is up.
    method: GET
    url: http://career-agent:8001/health
