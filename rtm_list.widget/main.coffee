command: "/Users/yina/.pyenv/shims/python /Users/yina/Dropbox/Backups/geektool/ubersicht_widgets/rtm_list.widget/rtm_cli.py -c -p ls list:now priority:1"

refreshFrequency: 10000

style: """
  top: 450px
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
