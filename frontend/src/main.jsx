import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const base = import.meta.env.BASE_URL;
function App() {
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState('all');
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${base}data/index.json`, { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error(`读取结果失败：HTTP ${response.status}`); return response.json(); })
      .then(setData).catch(error => { if (error.name !== 'AbortError') setError(error.message); });
    return () => controller.abort();
  }, []);
  const view = data?.views.find(item => item.id === selected);
  return <main>
    <h1>CS2 CT 防守站位热力图</h1>
    <p>手动收集的职业比赛 demo · 冻结结束后 10 秒至下包前 · 每 0.2 秒采样 · 仅存活 CT</p>
    <p>连续颜色表示本图相对密度，半透明显示；不同图片的颜色强度不能直接作绝对比较。</p>
    {error && <p role="alert">{error}</p>}
    {!data && !error && <p>加载中……</p>}
    {data && <>
      <p>{data.coverage}。更新时间：{new Date(data.updated_at).toLocaleString('zh-CN')}</p>
      <label>数据范围：<select value={selected} onChange={e => setSelected(e.target.value)}>
        {data.views.map(item => <option key={item.id} value={item.id}>{item.id === 'all' ? '历史总和' : item.name}{item.id === data.latest_event ? '（最新赛事）' : ''}</option>)}
      </select></label>
      <p>已导入 {view?.demo_count ?? 0} 个地图 demo</p>
      {!view?.images.length && <p>暂无结果，请先使用解析工具导入 demo。</p>}
      <section>{view?.images.map(item => <figure key={`${item.map}-${item.layer}`}>
        <figcaption>{item.map.toUpperCase()} {item.layer === 'upper' ? '上层' : item.layer === 'lower' ? '下层' : ''} · {item.player_seconds.toLocaleString()} 选手秒</figcaption>
        <a href={`${base}data/${item.url}`} target="_blank" rel="noreferrer"><img loading="lazy" src={`${base}data/${item.url}`} alt={`${item.map} ${item.layer} CT 防守热力图`}/></a>
      </figure>)}</section>
    </>}
  </main>;
}
createRoot(document.getElementById('root')).render(<App/>);
