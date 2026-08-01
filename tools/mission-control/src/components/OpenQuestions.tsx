"use client";

import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  FormControlLabel,
  Paper,
  Radio,
  RadioGroup,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import type { OpenQuestion } from "@/lib/types";

interface Props {
  runId: string;
  questions: OpenQuestion[];
  onAnswered: () => void;
}

/**
 * Review surface for everything the planner could not decide. Each question
 * offers the planner's options plus a free-text escape hatch; unanswered
 * questions that gate tasks keep those tasks out of dispatch.
 */
export function OpenQuestions({ runId, questions, onAnswered }: Props) {
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [custom, setCustom] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const unanswered = questions.filter((q) => !q.answer);
  if (questions.length === 0) return null;

  async function save() {
    setSaving(true);
    setError(null);
    const answers = unanswered
      .map((q) => {
        const optionId = selections[q.id];
        const text = optionId === "__custom__" ? custom[q.id]?.trim() : undefined;
        if (optionId === "__custom__") {
          return text ? { questionId: q.id, text } : null;
        }
        return optionId ? { questionId: q.id, optionId } : null;
      })
      .filter(Boolean);

    if (answers.length === 0) {
      setError("Select an answer for at least one question.");
      setSaving(false);
      return;
    }

    try {
      const response = await fetch(`/api/runs/${runId}/answers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error ?? "Could not save answers.");
      }
      setSelections({});
      setCustom({});
      onAnswered();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save answers.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Paper
      variant="outlined"
      sx={{ p: 2.5, mb: 3, borderColor: unanswered.length > 0 ? "warning.main" : undefined }}
    >
      <Stack direction="row" spacing={1.5} sx={{ mb: 2, alignItems: "center" }}>
        <Typography variant="h2">Open questions</Typography>
        <Chip
          size="small"
          color={unanswered.length > 0 ? "warning" : "success"}
          label={
            unanswered.length > 0 ? `${unanswered.length} awaiting you` : "all answered"
          }
        />
      </Stack>

      <Stack spacing={3}>
        {questions.map((question) => {
          const answered = Boolean(question.answer);
          const selected = selections[question.id] ?? "";
          return (
            <Box key={question.id}>
              <Typography variant="body1" sx={{ fontWeight: 600 }}>
                {question.question}
              </Typography>
              {question.context && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  {question.context}
                </Typography>
              )}
              {question.blocksTaskIds.length > 0 && (
                <Typography variant="caption" color="warning.main" sx={{ mt: 0.5, display: "block" }}>
                  Blocks: {question.blocksTaskIds.join(", ")}
                </Typography>
              )}

              {answered ? (
                <Alert severity="success" sx={{ mt: 1.5 }}>
                  {question.answer!.text}
                </Alert>
              ) : (
                <>
                  <RadioGroup
                    value={selected}
                    onChange={(e) =>
                      setSelections((s) => ({ ...s, [question.id]: e.target.value }))
                    }
                    sx={{ mt: 1 }}
                  >
                    {question.options.map((option) => (
                      <FormControlLabel
                        key={option.id}
                        value={option.id}
                        control={<Radio size="small" />}
                        sx={{ alignItems: "flex-start", mb: 0.5 }}
                        label={
                          <Box sx={{ pt: 0.75 }}>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              {option.label}
                              {option.recommended && (
                                <Chip
                                  size="small"
                                  color="primary"
                                  variant="outlined"
                                  label="Recommended"
                                  sx={{ ml: 1, height: 18, fontSize: "0.65rem" }}
                                />
                              )}
                            </Typography>
                            {option.detail && (
                              <Typography variant="caption" color="text.secondary">
                                {option.detail}
                              </Typography>
                            )}
                          </Box>
                        }
                      />
                    ))}
                    <FormControlLabel
                      value="__custom__"
                      control={<Radio size="small" />}
                      label={<Typography variant="body2">Something else…</Typography>}
                    />
                  </RadioGroup>
                  {selected === "__custom__" && (
                    <TextField
                      fullWidth
                      size="small"
                      multiline
                      minRows={2}
                      placeholder="Your answer"
                      value={custom[question.id] ?? ""}
                      onChange={(e) =>
                        setCustom((c) => ({ ...c, [question.id]: e.target.value }))
                      }
                    />
                  )}
                </>
              )}
            </Box>
          );
        })}
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}

      {unanswered.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Button variant="contained" onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save answers"}
          </Button>
        </Box>
      )}
    </Paper>
  );
}
