(ns gracie.projects.views
  (:require [framework.utils :as u]
            [cljs.pprint :refer [pprint]]))

(defn project-thumb
  [{:keys [url project]} & children]
  [:div.max-w-xs.w-full
   [:div.text-center
    [:div.relative.overflow-hidden {:style {:height "13.5rem"}}
     [:a.absolute.left-0.right-0.top-0.bottom-0.block
      {:href url,
       :style {:background-image
                 (str "url('" (:thumbnail project) "')"),
               :background-repeat "no-repeat",
               :background-size "cover",
               :background-position "center"}}]]
    [:h2.uppercase.text-lg.font-body.font-light
     (into [:a {:href url}] children)]]])
