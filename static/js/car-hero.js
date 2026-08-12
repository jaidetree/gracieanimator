const MAX_OPACITY = 20
const MIN_OPACITY = 5

function clamp(x, min, max) {
	return Math.min(Math.max(min, x), max)
}

/**
 * Given an activeIndex, calculate fall-off opacity relative to the selected
 * index.
 */
function updateImages(activeIndex) {
	const container = document.getElementById('car-hero')
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

document.addEventListener('mousemove', handleMouseMove)

updateImages(1)
