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
    headers:
      Authorization: "Bearer ${NEMO_API_KEY}"
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
    headers:
      Authorization: "Bearer ${NEMO_API_KEY}"

  - name: get_status
    description: >
      Retrieve detailed pipeline statistics including counts of ready,
      skipped, and processed job listings.
    method: GET
    url: http://career-agent:8001/status
    headers:
      Authorization: "Bearer ${NEMO_API_KEY}"

  - name: pause_agent
    description: >
      Pause the autonomous daily job search and application cycle.
    method: POST
    url: http://career-agent:8001/control
    headers:
      Authorization: "Bearer ${NEMO_API_KEY}"
    parameters:
      action:
        type: string
        required: true
        fixed: "pause"

  - name: resume_agent
    description: >
      Resume the autonomous daily job search and application cycle.
    method: POST
    url: http://career-agent:8001/control
    headers:
      Authorization: "Bearer ${NEMO_API_KEY}"
    parameters:
      action:
        type: string
        required: true
        fixed: "resume"

  - name: manual_trigger
    description: >
      Trigger an immediate job search and scoring cycle using the last
      successfully used search parameters.
    method: POST
    url: http://career-agent:8001/trigger
    headers:
      Authorization: "Bearer ${NEMO_API_KEY}"

  - name: get_benchmarks
    description: >
      Retrieve salary benchmarks and market averages for a specific job title and location.
      Trigger before negotiations to understand what to aim for.
    method: GET
    url: http://career-agent:8001/nego
    headers:
      Authorization: "Bearer ${NEMO_API_KEY}"
    parameters:
      role:
        type: string
        required: true
        description: "Target job title, e.g. 'Software Engineer'"
      location:
        type: string
        required: false
        default: "France"
        description: "Target location for the role"

  - name: prepare_for_interview
    description: >
      Generate a comprehensive 'Interview Briefing' for a specific job application.
      The dossier includes company news, strategy, and predicted interview questions.
    method: GET
    url: http://career-agent:8001/applications/{job_id}/prepare
    headers:
      Authorization: "Bearer ${NEMO_API_KEY}"
    parameters:
      job_id:
        type: string
        required: true
        description: "The unique ID of the job application"

  - name: research_company
    description: >
      Conduct ad-hoc web research on a specific company and generate a dossier
      for a specific role. Triggers a web search using DuckDuckGo.
    method: GET
    url: http://career-agent:8001/research
    headers:
      Authorization: "Bearer ${NEMO_API_KEY}"
    parameters:
      company:
        type: string
        required: true
        description: "The name of the target company"
      role:
        type: string
        required: false
        default: "General"
        description: "The specific role or job title to tailor the briefing towards"
