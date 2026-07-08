# QQAdapter.connect() `is_reconnect` Fix

## The Bug

After a `hermes update` (or fresh install), the QQ Bot adapter's `connect()` method
lacks the `is_reconnect` keyword argument that the base class and the gateway runner expect.

## Symptom

```
ERROR gateway.run: ✗ qqbot error: QQAdapter.connect() got an unexpected keyword argument 'is_reconnect'
WARNING gateway.run: Reconnect qqbot error: QQAdapter.connect() got an unexpected keyword argument 'is_reconnect', next retry in 60s
```

## One-liner Fix

```bash
cd /usr/local/lib/hermes-agent
sed -i 's/async def connect(self) -> bool:/async def connect(self, *, is_reconnect: bool = False) -> bool:/' \
  gateway/platforms/qqbot/adapter.py

# Verify:
python3 -c "
import ast
with open('gateway/platforms/qqbot/adapter.py') as f:
    tree = ast.parse(f.read())
for n in ast.walk(tree):
    if isinstance(n, ast.AsyncFunctionDef) and n.name == 'connect':
        assert 'is_reconnect' in ast.dump(n.args), 'Missing is_reconnect'
print('✅ Fix confirmed')
"
```

## Why This Happens

The base class `BasePlatformAdapter` at `gateway/platforms/base.py` defines:

```python
@abstractmethod
async def connect(self, *, is_reconnect: bool = False) -> bool:
```

But `QQAdapter` (in `gateway/platforms/qqbot/adapter.py`) omitted the kwarg —
it was written against an older interface. `gateway/run.py` calls
`await adapter.connect(is_reconnect=is_reconnect)`, which explodes.

## After `hermes update`

This fix is in the installed source tree under `/usr/local/lib/hermes-agent/gateway/`.
Every `hermes update` replaces the entire directory, so the fix is lost.

Always re-apply after updating. Check with:

```bash
grep -q "is_reconnect" /usr/local/lib/hermes-agent/gateway/platforms/qqbot/adapter.py && \
  echo "✅ Fix present" || echo "❌ Needs re-apply"
```
