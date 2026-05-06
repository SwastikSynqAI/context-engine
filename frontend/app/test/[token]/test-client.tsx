'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import { useParams } from 'next/navigation'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Question {
  question: string
  options: string[]
  index: number
}

interface Questions {
  aptitude: Question[]
  english: Question[]
  ai?: Question[]
  domain?: Question[]
}

interface TestSession {
  session_id: string
  status: string
  questions: Questions
}

interface SubmitResult {
  passed: boolean
  overall_score: number
  stage: string
}

type Phase = 'loading' | 'instructions' | 'testing' | 'submitting' | 'result' | 'error' | 'already_done'

// ── Constants ─────────────────────────────────────────────────────────────────

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const TOTAL_SECONDS = 35 * 60 // 2100

// ── Utility ───────────────────────────────────────────────────────────────────

function toListFormat(
  answers: Record<string, Record<number, number>>,
  questions: Questions
): Record<string, number[]> {
  const result: Record<string, number[]> = {}
  for (const [module, qs] of Object.entries(questions)) {
    result[module] = qs.map((q: Question) => answers[module]?.[q.index] ?? -1)
  }
  return result
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function totalQuestions(questions: Questions): number {
  return (
    questions.aptitude.length +
    questions.english.length +
    (questions.ai?.length ?? 0)
  )
}

function answeredCount(
  answers: Record<string, Record<number, number>>,
  questions: Questions
): number {
  let count = 0
  for (const [module, qs] of Object.entries(questions)) {
    for (const q of qs) {
      if (answers[module]?.[q.index] !== undefined) count++
    }
  }
  return count
}

// ── Sub-components (defined OUTSIDE TestClient) ───────────────────────────────

function TimerDisplay({ seconds }: { seconds: number }) {
  const urgent = seconds < 5 * 60
  return (
    <span
      style={{
        fontVariantNumeric: 'tabular-nums',
        fontWeight: 700,
        fontSize: 16,
        color: urgent ? '#ef4444' : '#a78bfa',
        minWidth: 52,
        display: 'inline-block',
        textAlign: 'right',
      }}
    >
      {formatTime(seconds)}
    </span>
  )
}

function OptionButton({
  label,
  text,
  selected,
  onClick,
}: {
  label: string
  text: string
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 12,
        width: '100%',
        textAlign: 'left',
        background: selected ? '#1a1428' : '#0d0d14',
        border: `1.5px solid ${selected ? '#7c3aed' : '#1e1e2e'}`,
        borderRadius: 8,
        padding: '12px 14px',
        cursor: 'pointer',
        color: selected ? '#f1f5f9' : '#94a3b8',
        fontSize: 14,
        transition: 'border-color 0.15s, background 0.15s',
        marginBottom: 8,
      }}
    >
      <span
        style={{
          flexShrink: 0,
          width: 24,
          height: 24,
          borderRadius: '50%',
          border: `1.5px solid ${selected ? '#7c3aed' : '#374151'}`,
          background: selected ? '#7c3aed22' : 'transparent',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 700,
          fontSize: 12,
          color: selected ? '#a78bfa' : '#6b7280',
        }}
      >
        {label}
      </span>
      <span style={{ lineHeight: 1.5, paddingTop: 2 }}>{text}</span>
    </button>
  )
}

function QuestionCard({
  question,
  questionNumber,
  totalQ,
  module,
  selectedIndex,
  onSelect,
}: {
  question: Question
  questionNumber: number
  totalQ: number
  module: string
  selectedIndex: number | undefined
  onSelect: (module: string, qIndex: number, optIndex: number) => void
}) {
  const labels = ['A', 'B', 'C', 'D']
  return (
    <div
      style={{
        background: '#12121a',
        border: '1px solid #1e1e2e',
        borderRadius: 12,
        padding: '20px 22px',
        marginBottom: 18,
      }}
    >
      <div style={{ color: '#6b7280', fontSize: 12, fontWeight: 600, marginBottom: 10 }}>
        Question {questionNumber} of {totalQ}
      </div>
      <p style={{ color: '#f1f5f9', fontSize: 15, fontWeight: 500, lineHeight: 1.6, marginBottom: 16, marginTop: 0 }}>
        {question.question}
      </p>
      <div>
        {question.options.map((opt, i) => (
          <OptionButton
            key={i}
            label={labels[i] ?? String(i + 1)}
            text={opt}
            selected={selectedIndex === i}
            onClick={() => onSelect(module, question.index, i)}
          />
        ))}
      </div>
    </div>
  )
}

function InstructionsScreen({
  questions,
  onStart,
}: {
  questions: Questions
  onStart: () => void
}) {
  const sections: { label: string; count: number }[] = [
    { label: 'Aptitude', count: questions.aptitude.length },
    { label: 'English', count: questions.english.length },
  ]
  if (questions.ai && questions.ai.length > 0) {
    sections.push({ label: 'AI Knowledge', count: questions.ai.length })
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#0a0a0f',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 16px',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <div
        style={{
          background: '#12121a',
          border: '1px solid #1e1e2e',
          borderRadius: 16,
          padding: '36px 40px',
          maxWidth: 540,
          width: '100%',
        }}
      >
        <div style={{ marginBottom: 24 }}>
          <div style={{ color: '#7c3aed', fontSize: 13, fontWeight: 700, letterSpacing: 1, marginBottom: 8, textTransform: 'uppercase' }}>
            YourCompany
          </div>
          <h1 style={{ color: '#f1f5f9', fontSize: 24, fontWeight: 800, margin: 0, lineHeight: 1.3 }}>
            Online Assessment — YourCompany
          </h1>
        </div>

        <div style={{ marginBottom: 24 }}>
          <div style={{ color: '#94a3b8', fontSize: 13, fontWeight: 600, marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>
            Sections
          </div>
          {sections.map((sec) => (
            <div
              key={sec.label}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                background: '#0d0d14',
                border: '1px solid #1e1e2e',
                borderRadius: 8,
                marginBottom: 8,
              }}
            >
              <span style={{ color: '#f1f5f9', fontWeight: 600, fontSize: 14 }}>{sec.label}</span>
              <span style={{ color: '#a78bfa', fontSize: 13, fontWeight: 700 }}>{sec.count} questions</span>
            </div>
          ))}
        </div>

        <div
          style={{
            background: '#0d0d14',
            border: '1px solid #1e1e2e',
            borderRadius: 8,
            padding: '16px 18px',
            marginBottom: 28,
          }}
        >
          <div style={{ color: '#94a3b8', fontSize: 13, fontWeight: 600, marginBottom: 10 }}>
            Instructions
          </div>
          <ul style={{ margin: 0, paddingLeft: 18, color: '#cbd5e1', fontSize: 14, lineHeight: 1.8 }}>
            <li>You have <strong style={{ color: '#f1f5f9' }}>35 minutes</strong> to complete the assessment.</li>
            <li>Answer all questions before submitting. The timer auto-submits when it reaches zero.</li>
            <li>Each question has exactly one correct answer — select the best option.</li>
            <li>Do not refresh the page; your progress is stored in the browser.</li>
          </ul>
        </div>

        <button
          onClick={onStart}
          style={{
            width: '100%',
            background: '#7c3aed',
            color: '#fff',
            border: 'none',
            borderRadius: 10,
            padding: '14px 0',
            fontSize: 16,
            fontWeight: 700,
            cursor: 'pointer',
            letterSpacing: 0.3,
          }}
        >
          Start Test →
        </button>
      </div>
    </div>
  )
}

function ResultScreen({
  result,
}: {
  result: SubmitResult
}) {
  const passed = result.passed
  const accent = passed ? '#10b981' : '#94a3b8'
  const bgAccent = passed ? '#10b98122' : '#1e1e2e'

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#0a0a0f',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 16px',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <div
        style={{
          background: '#12121a',
          border: `1px solid ${accent}`,
          borderRadius: 16,
          padding: '40px 44px',
          maxWidth: 480,
          width: '100%',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            width: 64,
            height: 64,
            borderRadius: '50%',
            background: bgAccent,
            border: `2px solid ${accent}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px',
            fontSize: 28,
          }}
        >
          {passed ? '✓' : '·'}
        </div>

        <h2 style={{ color: '#f1f5f9', fontSize: 22, fontWeight: 800, margin: '0 0 8px' }}>
          {passed ? 'Congratulations!' : 'Assessment Complete'}
        </h2>

        <p style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.6, marginBottom: 24 }}>
          {passed
            ? 'You have passed the YourCompany online assessment. Our team will be in touch shortly.'
            : 'Thank you for completing the assessment. We will review your results and get back to you.'}
        </p>

        <div
          style={{
            background: '#0d0d14',
            border: '1px solid #1e1e2e',
            borderRadius: 10,
            padding: '16px 20px',
            display: 'inline-block',
            minWidth: 160,
          }}
        >
          <div style={{ color: '#6b7280', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Your Score</div>
          <div style={{ color: accent, fontSize: 32, fontWeight: 800 }}>
            {Math.round(result.overall_score)}%
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Main Client Component ─────────────────────────────────────────────────────

export default function TestClient() {
  const params = useParams()
  const token = params?.token as string

  const [phase, setPhase] = useState<Phase>('loading')
  const [session, setSession] = useState<TestSession | null>(null)
  const [answers, setAnswers] = useState<Record<string, Record<number, number>>>({})
  const [activeModule, setActiveModule] = useState<string>('aptitude')
  const [timeLeft, setTimeLeft] = useState<number>(TOTAL_SECONDS)
  const [result, setResult] = useState<SubmitResult | null>(null)
  const [errorMsg, setErrorMsg] = useState<string>('')

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const answersRef = useRef<Record<string, Record<number, number>>>({})

  // Keep answersRef in sync so timer callback can access latest answers
  useEffect(() => {
    answersRef.current = answers
  }, [answers])

  // ── Load test session ───────────────────────────────────────────────────────

  useEffect(() => {
    if (!token) return

    async function fetchSession() {
      try {
        const res = await fetch(`${BASE_URL}/hr/test/${token}`)
        if (res.status === 404) {
          setErrorMsg('This assessment link is invalid or has expired.')
          setPhase('error')
          return
        }
        if (res.status === 410) {
          setPhase('already_done')
          return
        }
        if (!res.ok) {
          setErrorMsg(`Unable to load assessment (${res.status}).`)
          setPhase('error')
          return
        }
        const data: TestSession = await res.json()
        setSession(data)
        setPhase('instructions')
      } catch {
        setErrorMsg('Network error — please check your connection and try again.')
        setPhase('error')
      }
    }

    fetchSession()
  }, [token])

  // ── Submit handler ──────────────────────────────────────────────────────────

  const submitTest = useCallback(
    async (currentAnswers: Record<string, Record<number, number>>) => {
      if (!session) return
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
      setPhase('submitting')
      try {
        const body = toListFormat(currentAnswers, session.questions)
        const res = await fetch(`${BASE_URL}/hr/test/${token}/submit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        if (!res.ok) {
          const text = await res.text().catch(() => res.statusText)
          setErrorMsg(`Submission failed (${res.status}): ${text}`)
          setPhase('error')
          return
        }
        const data: SubmitResult = await res.json()
        setResult(data)
        setPhase('result')
      } catch {
        setErrorMsg('Network error during submission. Please try again.')
        setPhase('error')
      }
    },
    [session, token]
  )

  // ── Start test & timer ──────────────────────────────────────────────────────

  const startTest = useCallback(() => {
    setPhase('testing')
    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current!)
          timerRef.current = null
          // Auto-submit with current answers
          submitTest(answersRef.current)
          return 0
        }
        return prev - 1
      })
    }, 1000)
  }, [submitTest])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  // ── Answer selection ────────────────────────────────────────────────────────

  const selectAnswer = useCallback(
    (module: string, questionIndex: number, optionIndex: number) => {
      setAnswers((prev) => ({
        ...prev,
        [module]: {
          ...prev[module],
          [questionIndex]: optionIndex,
        },
      }))
    },
    []
  )

  // ── Handle submit button ────────────────────────────────────────────────────

  const handleSubmit = useCallback(() => {
    submitTest(answers)
  }, [answers, submitTest])

  // ── Phase: error ────────────────────────────────────────────────────────────

  if (phase === 'error') {
    return (
      <div
        style={{
          minHeight: '100vh',
          background: '#0a0a0f',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'system-ui, sans-serif',
          padding: 24,
        }}
      >
        <div
          style={{
            background: '#12121a',
            border: '1px solid #ef444444',
            borderRadius: 14,
            padding: '36px 40px',
            maxWidth: 440,
            textAlign: 'center',
          }}
        >
          <h2 style={{ color: '#f1f5f9', fontSize: 20, fontWeight: 700, marginBottom: 12 }}>
            Assessment Not Found
          </h2>
          <p style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.6, margin: 0 }}>
            {errorMsg}
          </p>
        </div>
      </div>
    )
  }

  // ── Phase: already_done ─────────────────────────────────────────────────────

  if (phase === 'already_done') {
    return (
      <div
        style={{
          minHeight: '100vh',
          background: '#0a0a0f',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'system-ui, sans-serif',
          padding: 24,
        }}
      >
        <div
          style={{
            background: '#12121a',
            border: '1px solid #1e1e2e',
            borderRadius: 14,
            padding: '36px 40px',
            maxWidth: 440,
            textAlign: 'center',
          }}
        >
          <h2 style={{ color: '#f1f5f9', fontSize: 20, fontWeight: 700, marginBottom: 12 }}>
            Already Completed
          </h2>
          <p style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.6, margin: 0 }}>
            This assessment has already been submitted. Each link can only be used once.
          </p>
        </div>
      </div>
    )
  }

  // ── Phase: loading ──────────────────────────────────────────────────────────

  if (phase === 'loading') {
    return (
      <div
        style={{
          minHeight: '100vh',
          background: '#0a0a0f',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        <div style={{ color: '#6b7280', fontSize: 16 }}>Loading assessment…</div>
      </div>
    )
  }

  // ── Phase: instructions ─────────────────────────────────────────────────────

  if (phase === 'instructions' && session) {
    return <InstructionsScreen questions={session.questions} onStart={startTest} />
  }

  // ── Phase: result ───────────────────────────────────────────────────────────

  if (phase === 'result' && result) {
    return <ResultScreen result={result} />
  }

  // ── Phase: submitting ───────────────────────────────────────────────────────

  if (phase === 'submitting') {
    return (
      <div
        style={{
          minHeight: '100vh',
          background: '#0a0a0f',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        <div style={{ color: '#a78bfa', fontSize: 16, fontWeight: 600 }}>Submitting your answers…</div>
      </div>
    )
  }

  // ── Phase: testing ──────────────────────────────────────────────────────────

  if (!session) return null

  const questions = session.questions
  const modules = Object.keys(questions) as Array<keyof Questions>
  const hasMultipleModules = modules.length > 1

  const moduleLabels: Record<string, string> = {
    aptitude: 'Aptitude',
    english: 'English',
    ai: 'AI Knowledge',
    domain: 'Domain Knowledge',
  }

  const currentModuleQuestions: Question[] = (questions[activeModule as keyof Questions] ?? []) as Question[]
  const total = totalQuestions(questions)
  const answered = answeredCount(answers, questions)
  const allAnswered = answered === total
  const remaining = total - answered

  // Compute question offset for display numbering
  let questionOffset = 0
  for (const mod of modules) {
    if (mod === activeModule) break
    questionOffset += (questions[mod as keyof Questions] ?? []).length
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#0a0a0f',
        fontFamily: 'system-ui, sans-serif',
        color: '#f1f5f9',
        paddingBottom: 80,
      }}
    >
      {/* Sticky header */}
      <div
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 10,
          background: '#12121a',
          borderBottom: '1px solid #1e1e2e',
          padding: '12px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <span style={{ fontWeight: 700, fontSize: 15, color: '#f1f5f9' }}>
            YourCompany Assessment
          </span>
          <span style={{ color: '#6b7280', fontSize: 13, marginLeft: 12 }}>
            {answered}/{total} answered
          </span>
        </div>
        <TimerDisplay seconds={timeLeft} />
      </div>

      {/* Module tabs */}
      {hasMultipleModules ? (
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid #1e1e2e',
            padding: '0 24px',
            background: '#0a0a0f',
          }}
        >
          {modules.map((mod) => {
            const isActive = mod === activeModule
            return (
              <button
                key={mod}
                onClick={() => setActiveModule(mod)}
                style={{
                  background: 'none',
                  border: 'none',
                  borderBottom: isActive ? '2px solid #7c3aed' : '2px solid transparent',
                  color: isActive ? '#a78bfa' : '#6b7280',
                  fontWeight: isActive ? 700 : 500,
                  fontSize: 14,
                  padding: '12px 18px',
                  cursor: 'pointer',
                  transition: 'color 0.15s',
                  marginBottom: -1,
                }}
              >
                {moduleLabels[mod] ?? mod}
              </button>
            )
          })}
        </div>
      ) : null}

      {/* Questions */}
      <div style={{ maxWidth: 680, margin: '0 auto', padding: '24px 20px' }}>
        {currentModuleQuestions.map((q, i) => (
          <QuestionCard
            key={`${activeModule}-${q.index}`}
            question={q}
            questionNumber={questionOffset + i + 1}
            totalQ={total}
            module={activeModule}
            selectedIndex={answers[activeModule]?.[q.index]}
            onSelect={selectAnswer}
          />
        ))}
      </div>

      {/* Fixed bottom bar */}
      <div
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          background: '#12121a',
          borderTop: '1px solid #1e1e2e',
          padding: '14px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span style={{ color: '#6b7280', fontSize: 14 }}>
          {remaining > 0
            ? `${remaining} question${remaining !== 1 ? 's' : ''} remaining`
            : 'All questions answered'}
        </span>
        <button
          onClick={handleSubmit}
          disabled={!allAnswered}
          style={{
            background: allAnswered ? '#7c3aed' : '#1e1e2e',
            color: allAnswered ? '#fff' : '#6b7280',
            border: 'none',
            borderRadius: 8,
            padding: '10px 24px',
            fontSize: 14,
            fontWeight: 700,
            cursor: allAnswered ? 'pointer' : 'not-allowed',
            transition: 'background 0.15s',
          }}
        >
          Submit Assessment
        </button>
      </div>
    </div>
  )
}
