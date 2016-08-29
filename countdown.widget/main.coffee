command: "/Users/yina/Dropbox/Backups/geektool/ubersicht_widgets/bin/simple_countdown.sh"

refreshFrequency: 5000

style: """
  top: 15px
  left: 390px
	*
		margin 0
		padding 0

	#container

		margin 0
		padding 0
		color rgba(#fff, .9)
		font-family Lucida Grande
		font-size 12pt


"""

render: (output) -> """
  #{output}
"""
