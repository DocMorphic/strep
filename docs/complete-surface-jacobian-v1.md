# Complete surface derivatives from pose derivatives

Development component, 2026-10-18. Retaining thousands of competing collision
points is expensive when each point repeats a backward pass through the whole
rig. These components separate pose differentiation, linear skinning and the
existing point/triangle feature derivative.

`SkinPoseJacobian` consumes complete joint poses and every supplied pose
derivative column. It returns every original vertex and its derivative,
streaming over bounded vertex chunks. All original influences are retained;
weights are neither normalized nor truncated. Input coefficients are owned,
and complete allocation checks reject oversized requests before constructing
the outputs. Chunk size changes working storage, not geometry or row coverage.

`CoupledMeshJacobian` uses the unchanged mesh-query implementation, then pulls
its source-point and target-triangle derivatives through supplied vertex
Jacobians. Explicit local-to-global column maps preserve independent actor
controls and correctly sum shared controls. Every source row and declared
global column is returned, including zeros. Current closest triangles and
barycentric weights remain a first-order local model; feature changes still
require independent nonlinear checks. No second derivatives, continuous
clearance, self-collision or physical-force claim is made.

Both components retain a 64 MiB complete-model allocation policy; they do not
raise the existing process-memory or motion limits. No row/column top-k
fallback is provided. Asset bindings and original author permissions remain
caller obligations.

All **307 focused source cases pass locally**, including the previous 264 and
43 new cases. Tests compare complete values and derivatives with the original
sparse skinning/autograd paths across influence counts and chunks, source and
target motion, arbitrary/shared column maps, ownership, receipt budgets and
invalid/incomplete inputs. Technical derivative comparisons add no physical
tolerance. Hosted and real full-surface probe results will be recorded when
complete.

A local capability probe computes all 924 pose components against all 36
controls per actor at frame 37 and checks projected reverse derivatives.
Forward and batched reverse differentiation are both supported on this
installation. Those timings are a single development probe, not a general
performance guarantee. Evidence: `reports/pose-jacobian-probe-v1` and
`reports/complete-surface-jacobian-tests-v1`.
