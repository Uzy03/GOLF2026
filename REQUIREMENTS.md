# REQUIREMENTS.md: NeuroGolf 2026 Challenge

## 1. Project Overview
This project aims to compete in the **Kaggle NeuroGolf 2026 Championship**. The goal is to design the "smallest possible neural network" for each task in the ARC-AGI (Abstraction and Reasoning Corpus) dataset. This is essentially **"Neural Code Golf"** where we minimize parameters and memory footprint while maintaining generalization.

## 2. Core Objective
Generate **400 individual ONNX models** (`task001.onnx` to `task400.onnx`) corresponding to the ARC-AGI training set. Each model must solve a specific task's underlying logic and generalize to hidden test cases of the same task.

## 3. Evaluation Metric (The "Golf" Score)
The score for a correctly solved task is calculated based on the following formulas:

$$Cost = (\text{Total Number of Parameters}) + (\text{Total Memory Footprint in Bytes})$$

$$Score = \max(1, 25 - \ln(Cost))$$

*   **Goal:** Minimize **Cost** to maximize the score.
*   **Note:** The model must be logically correct on hidden test cases to receive a score.

## 4. Technical Constraints (ONNX)
Models must strictly adhere to the following ONNX specifications:
*   **Static Shapes:** All tensor shapes and parameters must be statically defined (no dynamic axes).
*   **Forbidden Operators:** `Loop`, `Scan`, `NonZero`, `Unique`, `Script`, `Function` are **STRICTLY PROHIBITED**.
*   **Size Limit:** Each `.onnx` file must be under **1.44 MB**.
*   **Logic Representation:** Must use tensor operations (e.g., `Conv`, `Gather`, `Scatter`, `Where`, `Einsum`) to represent algorithmic logic instead of control flow.

## 5. Reference Strategy: MDL & Test-Time Optimization
The approach is inspired by the methodology in:
**"ARC-AGI Without Pretraining" (Liao & Gu, 2025) [arXiv:2512.06104]**.

### Key Principles:
*   **Minimum Description Length (MDL):** Treat puzzle-solving as finding the shortest neural program that explains the few-shot examples.
*   **Test-Time Optimization (TTO):** Optimize a small, flexible architecture on the given examples for each specific task at inference/generation time.
*   **Inductive Bias:** Utilize ARC-specific priors (color invariance, object persistence, grid symmetry) within a neural framework.

## 6. Functional Requirements for the System
1.  **Task Analyzer:** Parse ARC JSON files and identify input/output patterns.
2.  **Model Generator:** A pipeline that searches or optimizes for a minimal neural architecture per task.
3.  **TTO Solver:** A training/optimization loop that fits the tiny model to the examples while heavily penalizing the parameter count.
4.  **ONNX Compiler:** A robust exporter to convert PyTorch/JAX models to valid, static-shape ONNX files.
5.  **Local Evaluator:** Implement the `Cost` and `Score` calculation to rank models locally.

## 7. Immediate Roadmap
*   [ ] Build a utility to calculate the `Cost` metric from an ONNX file.
*   [ ] Create a "Hello World" ONNX exporter that satisfies all competition constraints (static shapes, no forbidden ops).
*   [ ] Analyze `arXiv:2512.06104` to extract primitive "neural modules" for ARC tasks.
*   [ ] Implement a basic TTO loop to optimize a 1-layer Conv model for a simple "color swap" task.