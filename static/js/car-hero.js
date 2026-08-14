const MAX_OPACITY = 10
const MIN_OPACITY = 0
const INTERVAL = 500

const totalFrames = document.querySelectorAll('.car-hero__frames img').length

function clamp(x, min, max) {
	return Math.min(Math.max(min, x), max)
}

function wrapIndex(index) {
	if (index >= totalFrames) {
		return 0
	}
	return index
}

/**
 * Given an activeIndex, calculate fall-off opacity relative to the selected
 * index.
 */
function updateImages(activeIndex) {
	const container = document.querySelector('.car-hero__frames')
	const previouslyActiveElements = Array.from(
		container.querySelectorAll('.active'),
	)

	previouslyActiveElements.forEach(el => {
		if (el) {
			// Remove the active class from the previously selected element
			el.classList.remove('active')
		}
	})

	for (let i = 0; i < 5; i += 1) {
		// Calculate the distance increment from the activeIndex
		const distance = Math.abs(i - activeIndex)

		// This is the item closest to the cursor
		if (distance === 0) {
			const el = container.children.item(i)
			el.classList.add('active')
			el.style.opacity = 1
		}
		// All the other items
		else {
			const opacity =
				(MAX_OPACITY - (distance - 1) * ((MAX_OPACITY - MIN_OPACITY) / 3)) / 100
			container.children.item(i).style.opacity = opacity
		}
	}
}

/**
 * Calculate the active index
 */
function handleMouseMove(e) {
	const mouseX = e.pageX
	const activeIndex = clamp(Math.floor((mouseX / window.innerWidth) * 5), 0, 4)

	updateImages(activeIndex)
}

const timeoutRef = { current: -1 }

function setAnimationTimeout(imgIndex) {
	return setTimeout(() => {
		updateImages(imgIndex)
		timeoutRef.current = setAnimationTimeout(wrapIndex(imgIndex + 1))
	}, INTERVAL)
}

timeoutRef.current = setAnimationTimeout(1)

function handleSliderChange(e) {
	const value = Number.parseInt(e.currentTarget.value) / 100
	const activeIndex = clamp(Math.floor(value * 5), 0, 4)

	if (timeoutRef.current > -1) {
		clearTimeout(timeoutRef.current)
		timeoutRef.current = -1
	}

	updateImages(activeIndex)
}

const slider = document.getElementById('car-hero-slider')

slider.addEventListener('input', handleSliderChange)

function handleSliderMouseDown() {
	document.querySelector('.car-hero__prompt').classList.add('active')
}

function handleSliderMouseUp() {
	document.querySelector('.car-hero__prompt').classList.remove('active')
}

slider.addEventListener('mousedown', handleSliderMouseDown)
slider.addEventListener('mouseup', handleSliderMouseUp)

updateImages(0)
