const params = Telegram.Utils.urlParseHashParams(location.hash);
const STICKER_ID = params['sticker_id'];
const SET_WIDTH = params['set_width'];
const SET_HEIGHT = params['set_height'];
const PART_WIDTH = params['part_width'];
const PART_HEIGHT = params['part_height'];
Telegram.WebApp.enableClosingConfirmation();
Telegram.WebApp.ready();


const logElement = document.getElementById('log');
const msgElement = document.getElementById('msg');

function log(type, message) {
	const bw = Math.abs(logElement.scrollHeight - logElement.scrollTop - logElement.clientHeight) < 1;
	logElement.innerHTML += `[${type}] ${message}<br>`;
	if (bw)
		logElement.scrollTop = logElement.clientHeight;
}
window.onerror = function(message) {
	log("error", message)
}
function setMessage(text) {
	msgElement.innerHTML = text;
	if (text) msgElement.style.display = '';
	else msgElement.style.display = 'none';
};

const progressElement = document.getElementsByClassName('progress-line')[0];
function showProgress() {
	progressElement.style.display = "";
}
function hideProgress() {
	progressElement.style.display = "none";
}

let ffmpeg = null;
const { createFFmpeg, fetchFile } = FFmpeg;
const pages = 2047;
const max_pages = 8191;
const initial_size = 64 * pages * 1024; // 64 KiB * 2048 = 128 MB
const max_size = 64 * max_pages * 1024; // 64 KiB * 8192 = 512 MB
// 1 page = 64 KiB

const init  = async () => {
	log('info', 'creating ffmpeg..');
	if (ffmpeg === null)
		ffmpeg = createFFmpeg(
			{
				log: true, corePath: 'static/js/ffmpeg-core.js',
				logger: ({type, message}) => log(type, message)
		        },
			{
				INITIAL_MEMORY: initial_size,
				wasmMemory: new WebAssembly.Memory({initial: pages, maximum: max_pages, shared: 1})
			}
		);

	setMessage('loading ffmpeg..');
	showProgress();
	if (!ffmpeg.isLoaded()) {
		await ffmpeg.load();
	}
	setMessage('');
	hideProgress();
};

async function split_part(n, name, width, height, part_width, part_height) {
	const y = Math.floor(n / width);
	const x = n % width;
	const out_name = `part_${n}.webm`;
	/* VERY UNNACCURATE BENCHMARK
	 * scaling algos:
	 * bicubic ~0.06x
	 * bicublin ~0.06x
	 * bitexact ~0.06x
	 * lanczos ~0.055x
	 * spline ~0.055x
	 * gauss ~0.055x
	 * sinc ~0.055x
	 * bilinear ~0.05x
	 * fast bilinear ~0.05x
	 * area ~0.05x
	 * experimental ~0.04x
	 * neighbour ~0.03x
	 */
	await ffmpeg.run(
		'-i', name,
		'-deadline', 'realtime',
		'-c:v', 'libvpx-vp9',
		'-b:v', '0',
		'-crf', '10',
		'-filter:v',
		`crop=iw/${width}:ih/${height}:${x}*iw/${width}:${y}*ih/${height}:1:1,scale=eval=init:interl=0:${part_width}x${part_height}:flags=bicubic`,
		out_name)
	const data = ffmpeg.FS('readFile', out_name);
	const new_blob = new Blob([data.buffer], {type: 'video/webm'});
	return new_blob
}

function createVideo(id) {
	const v = document.createElement('video');
	v.muted = true;
	v.loop = true;
	v.autoplay = true;
	v.id = id;
	v.onloadeddata = async () => {
		for (let v of document.getElementsByTagName("video")) {
			v.pause();
			v.currentTime = 0;
		}
		Array.from(document.getElementsByTagName("video")).forEach(v => v.play().catch(() => {}));
	}
	return v
}

function getStickerURL(width, height, part_width, part_height) {
	return `sticker/${STICKER_ID}/${width}x${height}-${part_width}x${part_height}`
}

async function fetchInherit(...args) {
	args[0] = args[0] + "?" + Telegram.WebApp.initData;
	const r = await fetch(...args);
	if (r.status != 200) Telegram.WebApp.close();
	return r
}

async function split(blob, width, height, part_width, part_height) {
	const name = STICKER_ID + ".webm";
	const grid = document.querySelector('#partsGrid');
	const r = await fetchInherit(`sticker/${STICKER_ID}/${width}x${height}/lastPart`);
	const last_part = parseInt(await r.text());
	grid.style['grid-template-columns'] = `repeat(${width}, 1fr)`;
	for (let i = 0; i < last_part; i++) {
		const vid = createVideo(`vid${i}`);
		vid.src = `${getStickerURL(width, height, part_width, part_height)}/${i}`
		grid.appendChild(vid);
	}
	setMessage(`${last_part} stickers were cached`);
	if (last_part < width * height) {
		ffmpeg.FS('writeFile', name, await fetchFile(blob));
		showProgress()
		let promises = [];
		for (let i = last_part + 1; i < width * height; i++) {
			const vid = createVideo(`vid${i}`);
			grid.appendChild(vid);
			p = async (lock) => {
				try {
					setMessage(`splitting part ${i}..`);
					let res = await split_part(i, name, width, height, part_width, part_height);
					vid.src = URL.createObjectURL(res);
					const formData = new FormData();
					formData.append('part', res, 'part.webm');
					await fetchInherit(`${getStickerURL(width, height, part_width, part_height)}/${i}`, {method: 'POST', body: formData, });
					return res;
				} catch (e) {
					console.log(e);
					log('error', e.toString())
				}
			};
			promises.push(navigator.locks.request('ffmpeg', p));
		}
		parts = await Promise.all(promises);
		hideProgress()

		return parts
	}
}


async function loadVideo() {
	const src = getStickerURL(SET_WIDTH, SET_HEIGHT, PART_WIDTH, PART_HEIGHT);
	videoBlob = await (await fetchInherit(src)).blob();
	const videoUrl = URL.createObjectURL(videoBlob);
	const video = document.querySelector('#originalVideo');
	video.muted = true;
	video.src = videoUrl;
	video.load();

	const parts = await split(videoBlob, SET_WIDTH, SET_HEIGHT, PART_WIDTH, PART_HEIGHT);
	console.log(parts);
	Telegram.WebApp.sendData(`done${STICKER_ID}-${SET_WIDTH}x${SET_HEIGHT}`);
}

loadVideo();
